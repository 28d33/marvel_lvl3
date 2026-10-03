<?php

class AttachmentRepo
{
    public static function findById(int $id): ?array
    {
        return Db::fetch('SELECT * FROM ATTACHMENT WHERE AttachmentID = ?', [$id]);
    }

    public static function findByItem(int $itemId): array
    {
        return Db::fetchAll('SELECT * FROM ATTACHMENT WHERE ItemID = ? ORDER BY CreatedAt DESC', [$itemId]);
    }

    public static function create(int $itemId, string $fileName, string $mimeType, int $fileSize): int
    {
        return Db::insert(
            'INSERT INTO ATTACHMENT (ItemID, FileName, MimeType, FileSize) VALUES (?, ?, ?, ?)',
            [$itemId, $fileName, $mimeType, $fileSize]
        );
    }

    public static function delete(int $id): void
    {
        Db::execute('DELETE FROM ATTACHMENT WHERE AttachmentID = ?', [$id]);
    }

    public static function addChunk(int $attachmentId, int $chunkNo, string $data): void
    {
        Db::execute(
            'INSERT INTO FILE_CHUNK (AttachmentID, ChunkNo, EncryptedData) VALUES (?, ?, ?)
             ON DUPLICATE KEY UPDATE EncryptedData=VALUES(EncryptedData)',
            [$attachmentId, $chunkNo, $data]
        );
    }

    public static function getChunk(int $attachmentId, int $chunkNo): ?array
    {
        return Db::fetch(
            'SELECT * FROM FILE_CHUNK WHERE AttachmentID = ? AND ChunkNo = ?',
            [$attachmentId, $chunkNo]
        );
    }

    public static function getChunks(int $attachmentId): array
    {
        return Db::fetchAll(
            'SELECT * FROM FILE_CHUNK WHERE AttachmentID = ? ORDER BY ChunkNo ASC',
            [$attachmentId]
        );
    }

    public static function chunkCount(int $attachmentId): int
    {
        $row = Db::fetch('SELECT COUNT(*) as cnt FROM FILE_CHUNK WHERE AttachmentID = ?', [$attachmentId]);
        return (int)($row['cnt'] ?? 0);
    }
}
