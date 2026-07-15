import pytest
from unittest.mock import patch, MagicMock, AsyncMock

MOCK_DRIVE_FILES = [
    {
        "gdrive_id": "drive-file-1",
        "name": "Syllabus.pdf",
        "mime_type": "application/pdf",
        "md5_checksum": "checksum1",
    },
    {
        "gdrive_id": "drive-file-2",
        "name": "Policies.docx",
        "mime_type": "application/vnd.google-apps.document",
        "md5_checksum": "checksum2",
    }
]

MOCK_DB_FILES = [
    {
        "id": "db-file-1",
        "gdrive_id": "drive-file-1",
        "name": "Syllabus.pdf",
        "mime_type": "application/pdf",
        "md5_checksum": "old-checksum", # Modified
        "updated_at": "2026-07-15T00:00:00Z"
    },
    {
        "id": "db-file-3",
        "gdrive_id": "drive-file-3",
        "name": "OldFile.txt",
        "mime_type": "text/plain",
        "md5_checksum": "checksum3", # Deleted from drive
        "updated_at": "2026-07-15T00:00:00Z"
    }
]

@pytest.fixture
def mock_admin_auth():
    with patch("routes.rag._extract_user_id", return_value="admin-user"), \
         patch("routes.rag._require_admin", return_value=None):
        yield

@pytest.fixture
def mock_rag_supabase():
    with patch("routes.rag.get_supabase_client") as mock:
        yield mock

def test_get_rag_delta(client, mock_admin_auth, mock_rag_supabase):
    class RagFilesMockTable:
        def select(self, *args, **kwargs):
            return self
        def execute(self):
            return MagicMock(data=MOCK_DB_FILES)
            
    mock_rag_supabase.return_value.table = lambda name: RagFilesMockTable()

    with patch("routes.rag._list_drive_files", return_value=MOCK_DRIVE_FILES):
        response = client.get("/api/rag/delta", headers={"Authorization": "Bearer token"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_changes"] == 3
        
        # New: drive-file-2
        assert len(data["new"]) == 1
        assert data["new"][0]["gdrive_id"] == "drive-file-2"
        
        # Modified: drive-file-1 (checksum mismatch)
        assert len(data["modified"]) == 1
        assert data["modified"][0]["gdrive_id"] == "drive-file-1"
        
        # Deleted: drive-file-3 (not in drive files)
        assert len(data["deleted"]) == 1
        assert data["deleted"][0]["gdrive_id"] == "drive-file-3"

def test_sync_single_file(client, mock_admin_auth, mock_rag_supabase):
    class SyncMockTable:
        def __init__(self, name):
            self.name = name
            self.data = []
        def select(self, *args, **kwargs): return self
        def eq(self, *args, **kwargs): return self
        def delete(self, *args, **kwargs): return self
        def insert(self, data, *args, **kwargs): 
            self.data = data if isinstance(data, list) else [data]
            self._inserted = True
            return self
        def execute(self):
            # For select, return empty to simulate no existing record
            if self.name == "rag_files" and not hasattr(self, "_inserted"):
                return MagicMock(data=[])
            # For insert, return the inserted data with a fake ID
            return MagicMock(data=[{**d, "id": f"new-id-{i}"} for i, d in enumerate(self.data)])

    mock_rag_supabase.return_value.table = lambda name: SyncMockTable(name)

    with patch("routes.rag._list_drive_files", return_value=MOCK_DRIVE_FILES), \
         patch("routes.rag._download_file_content", return_value="This is some content. " * 50), \
         patch("routes.rag.get_hybrid_client") as mock_get_client:
        
        class FakeLLM:
            async def embed(self, *args, **kwargs):
                return [0.1] * 768
                
        mock_get_client.return_value = FakeLLM()
        
        response = client.post("/api/rag/sync-file?gdrive_id=drive-file-1", headers={"Authorization": "Bearer token"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["gdrive_id"] == "drive-file-1"
        assert data["status"] == "synced"
        assert data["chunks_created"] > 0

def test_delete_rag_file(client, mock_admin_auth, mock_rag_supabase):
    class DeleteMockTable:
        def delete(self, *args, **kwargs): return self
        def eq(self, *args, **kwargs): return self
        def execute(self): return MagicMock(data=[{"id": "deleted"}])
        
    mock_rag_supabase.return_value.table = lambda name: DeleteMockTable()
    
    response = client.delete("/api/rag/file?gdrive_id=drive-file-1", headers={"Authorization": "Bearer token"})
    
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

def test_get_rag_stats(client, mock_admin_auth, mock_rag_supabase):
    class StatsMockTable:
        def __init__(self, name):
            self.name = name
        def select(self, *args, **kwargs): return self
        def eq(self, *args, **kwargs): return self
        def execute(self):
            if self.name == "rag_files":
                return MagicMock(data=MOCK_DB_FILES)
            if self.name == "rag_chunks":
                mock = MagicMock(data=[])
                mock.count = 42
                return mock
            return MagicMock(data=[])
            
    mock_rag_supabase.return_value.table = lambda name: StatsMockTable(name)
    
    response = client.get("/api/rag/stats", headers={"Authorization": "Bearer token"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_files"] == 2
    assert data["total_chunks"] == 42
    assert len(data["files"]) == 2
