from pathlib import Path
from types import SimpleNamespace

from app.core import upload_storage


class FakeS3:
    def __init__(self):
        self.uploads = []
        self.downloads = []
        self.deletes = []

    def upload_file(self, local_path, bucket, key):
        self.uploads.append((Path(local_path).read_bytes(), bucket, key))

    def download_file(self, bucket, key, local_path):
        self.downloads.append((bucket, key))
        Path(local_path).write_bytes(b"%PDF-1.7")

    def delete_object(self, *, Bucket, Key):
        self.deletes.append((Bucket, Key))


def test_s3_upload_download_and_delete_share_reference(tmp_path, monkeypatch):
    settings = SimpleNamespace(
        upload_storage_backend="s3",
        s3_bucket="research-pdfs",
        s3_endpoint_url="https://objects.example.test",
        s3_region="auto",
        s3_access_key_id="access",
        s3_secret_access_key="secret",
    )
    fake = FakeS3()
    monkeypatch.setattr(upload_storage, "get_settings", lambda: settings)
    monkeypatch.setattr(upload_storage, "_s3_client", lambda: fake)
    source = tmp_path / "upload.pdf"
    source.write_bytes(b"%PDF-1.7")

    reference = upload_storage.upload_pdf(source, "uploads/doc.pdf")
    materialized, temporary = upload_storage.materialize_pdf(reference)
    upload_storage.delete_upload(reference)

    assert reference == "s3://research-pdfs/uploads/doc.pdf"
    assert fake.uploads == [(b"%PDF-1.7", "research-pdfs", "uploads/doc.pdf")]
    assert fake.downloads == [("research-pdfs", "uploads/doc.pdf")]
    assert materialized.read_bytes() == b"%PDF-1.7"
    assert temporary is True
    assert fake.deletes == [("research-pdfs", "uploads/doc.pdf")]
    materialized.unlink()


def test_local_upload_storage_keeps_existing_path(tmp_path, monkeypatch):
    monkeypatch.setattr(upload_storage, "get_settings", lambda: SimpleNamespace(upload_storage_backend="local"))
    path = tmp_path / "local.pdf"

    assert upload_storage.upload_pdf(path, "unused") == str(path)
