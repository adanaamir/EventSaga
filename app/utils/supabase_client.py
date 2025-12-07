"""
Supabase Client Wrapper - Fixed Version
"""
import os
from supabase import create_client, Client
from typing import Optional

class SupabaseClient:
    """Singleton Supabase client"""
    _instance: Optional[Client] = None
    _service_instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase client instance"""
        if cls._instance is None:
            url = os.getenv('SUPABASE_URL')
            key = os.getenv('SUPABASE_ANON_KEY')
            
            if not url or not key:
                raise ValueError("Supabase credentials not found in environment")
            
            # Create client without proxy parameter
            cls._instance = create_client(url, key)
            print("✅ Supabase client initialized")
        
        return cls._instance
    
    @classmethod
    def get_service_client(cls) -> Client:
        """Get Supabase client with service role key (bypass RLS)"""
        if cls._service_instance is None:
            url = os.getenv('SUPABASE_URL')
            service_key = os.getenv('SUPABASE_SERVICE_KEY')
            
            if not url or not service_key:
                raise ValueError("Supabase service credentials not found")
            
            # Create service client without proxy parameter
            cls._service_instance = create_client(url, service_key)
            print("✅ Supabase service client initialized")
        
        return cls._service_instance

# Export singleton instance
def get_supabase() -> Client:
    """Get Supabase client instance"""
    return SupabaseClient.get_client()

def get_supabase_admin() -> Client:
    """Get Supabase admin client (service role)"""
    return SupabaseClient.get_service_client()