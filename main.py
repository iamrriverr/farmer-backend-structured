# main.py
"""
農會 RAG 系統 - 主要應用程式入口
FastAPI 應用初始化、路由註冊、中介層設定
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent))

# ✅ 導入新的配置模組
from src.core.config import Config, LLMConfig, PromptTemplates
from src.core.exceptions import BusinessException
from src.api.v1 import register_all_routers
from src.api.middleware import setup_all_middleware
from src.infrastructure import DatabaseConnection, VectorStoreManager


# ============================================================
# 1. 驗證配置（最先執行）
# ============================================================

try:
    Config.validate()
    print("\n✅ 配置驗證通過")
    Config.print_config()  # ✅ 使用 Config 的 print_config 方法
except Exception as e:
    print(f"\n❌ 配置驗證失敗: {e}\n")
    sys.exit(1)


# ============================================================
# 2. 建立 FastAPI 應用
# ============================================================

app = FastAPI(
    title=Config.TITLE,
    version=Config.VERSION,
    description=Config.DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# ============================================================
# 3. 設定 CORS（必須在 middleware 之前）
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開發模式允許所有來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 4. 設定 Middleware（必須在 startup 之前）
# ============================================================

setup_all_middleware(app, Config)


# ============================================================
# 5. 註冊路由（可以在 startup 之前或之後）
# ============================================================

print("\n註冊 API 路由:")
register_all_routers(app)
print("✅ 所有路由註冊完成\n")


# ============================================================
# 全域變數（資料庫連線、向量庫）
# ============================================================

db_connection = None
vector_store = None


# ============================================================
# 6. 啟動事件（只做資料庫初始化）
# ============================================================

@app.on_event("startup")
async def startup_event():
    """
    應用啟動時執行
    - 初始化資料庫連線
    - 初始化向量資料庫
    """
    global db_connection, vector_store
    
    print("\n" + "="*60)
    print(f"🚀 {Config.TITLE} v{Config.VERSION} 正在啟動...")
    print("="*60 + "\n")
    
    # 1. 初始化資料庫連線
    try:
        db_connection = DatabaseConnection(Config)
        if db_connection.test_connection():
            print("✅ PostgreSQL 連線成功")
        else:
            raise Exception("資料庫連線測試失敗")
    except Exception as e:
        print(f"❌ PostgreSQL 連線失敗: {e}")
        sys.exit(1)
    
    # 2. 初始化向量資料庫
    try:
        # ✅ 根據 LLMConfig 決定使用哪種 Embeddings
        use_gemini = (LLMConfig.PRIMARY_LLM == "gemini")
        
        vector_store = VectorStoreManager(
            config=Config,
            use_gemini=use_gemini
        )
        
        count = vector_store.get_collection_count()
        embedding_info = vector_store.get_embedding_info()  # ✅ 取得 Embedding 資訊
        
        print(f"✅ Chroma 向量資料庫已就緒")
        print(f"   - Collection: {vector_store.collection_name}")
        print(f"   - 文件數: {count}")
        print(f"   - Embedding: {embedding_info['provider']} ({embedding_info['model']})")
        
    except Exception as e:
        print(f"⚠️ Chroma 向量資料庫初始化警告: {e}")
        print("   系統將繼續運行，但 RAG 功能可能受限")
    
    print("\n" + "="*60)
    print(f"✅ {Config.TITLE} 啟動成功！")
    print("="*60)
    print(f"\n📖 API 文檔: http://localhost:8000/docs")
    print(f"🔧 健康檢查: http://localhost:8000/health")
    print(f"⚙️ 系統資訊: http://localhost:8000/api/v1/system/info\n")


# ============================================================
# 7. 關閉事件
# ============================================================

@app.on_event("shutdown")
async def shutdown_event():
    """
    應用關閉時執行
    - 關閉資料庫連線
    - 清理資源
    """
    global db_connection
    
    print("\n" + "="*60)
    print(f"🛑 {Config.TITLE} 正在關閉...")
    print("="*60)
    
    if db_connection:
        db_connection.close_pool()
        print("✅ PostgreSQL 連線池已關閉")
    
    print("✅ 所有資源已清理")
    print("="*60 + "\n")


# ============================================================
# 健康檢查端點
# ============================================================

@app.get("/", tags=["系統"])
async def root():
    """根路徑 - 系統資訊"""
    return {
        "title": Config.TITLE,
        "version": Config.VERSION,
        "description": Config.DESCRIPTION,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "system_info": "/api/v1/system/info"
    }


@app.get("/health", tags=["系統"])
async def health_check():
    """
    健康檢查端點
    檢查系統各組件狀態
    """
    health_status = {
        "status": "healthy",
        "version": Config.VERSION,
        "components": {}
    }
    
    # 檢查資料庫
    try:
        if db_connection and db_connection.test_connection():
            health_status["components"]["database"] = {
                "status": "healthy",
                "type": "PostgreSQL",
                "host": Config.PG_HOST,
                "database": Config.PG_DATABASE
            }
        else:
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "error": "連線失敗"
            }
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # 檢查向量資料庫
    try:
        if vector_store:
            count = vector_store.get_collection_count()
            embedding_info = vector_store.get_embedding_info()
            
            health_status["components"]["vector_store"] = {
                "status": "healthy",
                "type": "Chroma",
                "collection": vector_store.collection_name,
                "document_count": count,
                "embedding": embedding_info
            }
        else:
            health_status["components"]["vector_store"] = {
                "status": "not_initialized"
            }
    except Exception as e:
        health_status["components"]["vector_store"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # ✅ LLM 配置（使用 LLMConfig）
    health_status["components"]["llm"] = {
        "status": "configured",
        **LLMConfig.get_model_info()  # ✅ 自動取得模型資訊
    }
    
    return health_status


# ✅ 新增：系統資訊端點
@app.get("/api/v1/system/info", tags=["系統"])
async def system_info():
    """
    系統資訊端點
    提供完整的系統配置資訊
    """
    return {
        "system": {
            "title": Config.TITLE,
            "version": Config.VERSION,
            "description": Config.DESCRIPTION
        },
        "llm": LLMConfig.get_model_info(),
        "database": {
            "type": "PostgreSQL",
            "host": Config.PG_HOST,
            "port": Config.PG_PORT,
            "database": Config.PG_DATABASE
        },
        "vector_store": {
            "type": "Chroma",
            "collection": Config.CHROMA_COLLECTION,
            "persist_directory": Config.CHROMA_PERSIST_DIR,
            "embedding": vector_store.get_embedding_info() if vector_store else None
        },
        "rag_config": {
            "chunk_size": Config.CHUNK_SIZE,
            "chunk_overlap": Config.CHUNK_OVERLAP,
            "top_k": Config.RAG_TOP_K
        },
        "security": {
            "internal_network_only": Config.INTERNAL_NETWORK_ONLY,
            "jwt_algorithm": Config.ALGORITHM,
            "token_expire_minutes": Config.ACCESS_TOKEN_EXPIRE_MINUTES
        }
    }


# ✅ 新增：Prompt 管理端點
@app.get("/api/v1/system/prompts", tags=["系統"])
async def get_prompts():
    """
    取得所有 Prompt 模板
    用於管理和調試 Prompt
    """
    return {
        "prompts": PromptTemplates.get_all_prompts(),
        "note": "這些 Prompt 模板定義在 src/core/config/prompts.py"
    }


# ✅ 新增：配置更新端點（僅限管理員，生產環境應移除）
@app.post("/api/v1/system/config/reload", tags=["系統"])
async def reload_config():
    """
    重新載入配置（開發用）
    ⚠️ 生產環境應移除此端點
    """
    try:
        Config.validate()
        return {
            "status": "success",
            "message": "配置已重新載入",
            "config": LLMConfig.get_model_info()
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"配置載入失敗: {str(e)}"
            }
        )


# ============================================================
# 主程式入口
# ============================================================

if __name__ == "__main__":
    """
    直接運行 main.py 時啟動 uvicorn 伺服器
    
    開發模式：
        python main.py
        uvicorn main:app --reload

    
    生產模式：
        uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
    """
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 開發模式
        log_level="info"
    )
