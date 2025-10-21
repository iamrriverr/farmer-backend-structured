# src/api/middleware/ip_whitelist.py
"""
IP 白名單中介層
用於農會內網部署，限制只允許特定 IP 存取
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List, Callable
import ipaddress


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    IP 白名單驗證中介層
    
    只允許白名單內的 IP 地址存取 API
    """
    
    def __init__(self, app, allowed_ips: List[str] = None, 
                 allowed_networks: List[str] = None,
                 enable: bool = True):
        """
        初始化 IP 白名單中介層
        
        Args:
            app: FastAPI 應用
            allowed_ips: 允許的 IP 地址列表
            allowed_networks: 允許的網段列表（CIDR 格式）
            enable: 是否啟用（預設啟用）
        """
        super().__init__(app)
        self.enable = enable
        self.allowed_ips = set(allowed_ips or [])
        self.allowed_networks = [
            ipaddress.ip_network(net) for net in (allowed_networks or [])
        ]
        
        # 預設允許本地存取
        if not self.allowed_ips and not self.allowed_networks:
            self.allowed_ips.add("127.0.0.1")
            self.allowed_ips.add("::1")
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        驗證請求來源 IP
        
        Args:
            request: 請求物件
            call_next: 下一個處理器
            
        Returns:
            Response: 回應物件
            
        Raises:
            HTTPException: 當 IP 不在白名單時
        """
        # 如果未啟用，直接通過
        if not self.enable:
            return await call_next(request)
        
        # 取得客戶端 IP
        client_ip = self._get_client_ip(request)
        
        # 檢查是否在白名單
        if not self._is_ip_allowed(client_ip):
            print(f"⚠️ 拒絕來自 {client_ip} 的存取")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="存取被拒絕：您的 IP 地址不在允許的範圍內"
            )
        
        # 通過驗證，繼續處理
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """
        取得客戶端真實 IP
        
        考慮反向代理（Nginx）的情況
        
        Args:
            request: 請求物件
            
        Returns:
            str: 客戶端 IP
        """
        # 檢查 X-Forwarded-For header（反向代理）
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # 取第一個 IP（最原始的客戶端 IP）
            return forwarded_for.split(",")[0].strip()
        
        # 檢查 X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # 使用直接連線的 IP
        return request.client.host if request.client else "unknown"
    
    def _is_ip_allowed(self, ip_str: str) -> bool:
        """
        檢查 IP 是否在白名單
        
        Args:
            ip_str: IP 地址字串
            
        Returns:
            bool: 是否允許
        """
        try:
            ip = ipaddress.ip_address(ip_str)
            
            # 檢查精確匹配
            if ip_str in self.allowed_ips:
                return True
            
            # 檢查網段匹配
            for network in self.allowed_networks:
                if ip in network:
                    return True
            
            return False
            
        except ValueError:
            # IP 格式錯誤
            print(f"❌ 無效的 IP 格式: {ip_str}")
            return False


def is_internal_ip(ip_str: str) -> bool:
    """
    檢查是否為內網 IP
    
    Args:
        ip_str: IP 地址字串
        
    Returns:
        bool: 是否為內網 IP
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        
        # 檢查是否為私有 IP
        return ip.is_private or ip.is_loopback
        
    except ValueError:
        return False


def setup_ip_whitelist_middleware(app, config):
    """
    註冊 IP 白名單中介層到 FastAPI 應用
    
    Args:
        app: FastAPI 應用實例
        config: 配置物件
    """
    # 從配置讀取設定
    enable = getattr(config, "INTERNAL_NETWORK_ONLY", False)
    allowed_ips = getattr(config, "ALLOWED_IPS", [])
    
    # 預設農會內網網段（範例）
    allowed_networks = getattr(config, "ALLOWED_NETWORKS", [
        "192.168.0.0/16",   # 私有網段
        "10.0.0.0/8",       # 私有網段
        "172.16.0.0/12"     # 私有網段
    ])
    
    if enable:
        app.add_middleware(
            IPWhitelistMiddleware,
            allowed_ips=allowed_ips,
            allowed_networks=allowed_networks,
            enable=True
        )
        print(f"✅ IP 白名單中介層已啟用 - 允許 {len(allowed_ips)} 個 IP，{len(allowed_networks)} 個網段")
    else:
        print("ℹ️  IP 白名單中介層已停用（開發模式）")
