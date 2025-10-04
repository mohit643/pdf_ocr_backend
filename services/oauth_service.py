"""
OAuth Service - Google OAuth Implementation
"""
from typing import Optional, Dict
import httpx
from fastapi import HTTPException

class OAuthService:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.google_token_url = "https://oauth2.googleapis.com/token"
        self.google_userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate Google OAuth authorization URL"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile https://www.googleapis.com/auth/drive.file",  # Added Drive scope
            "access_type": "offline",
            "prompt": "consent"
        }
        
        if state:
            params["state"] = state
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.google_auth_url}?{query_string}"

    async def exchange_code_for_token(self, code: str) -> Dict:
        """Exchange authorization code for access token"""
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.google_token_url, data=data)
            
            if response.status_code != 200:
                raise HTTPException(400, "Failed to get access token")
            
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict:
        """Get user information from Google"""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.google_userinfo_url, headers=headers)
            
            if response.status_code != 200:
                raise HTTPException(400, "Failed to get user info")
            
            return response.json()