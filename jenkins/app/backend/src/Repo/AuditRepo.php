<?php

class AuditRepo
{
    public static function log(int $userId, ?int $itemId, string $action): void
    {
        Db::insert('INSERT INTO AUDIT_LOG (UserID, ItemID, Action) VALUES (?, ?, ?)', [$userId, $itemId, $action]);
    }

    public static function findByUser(int $userId, int $limit = 100): array
    {
        return Db::fetchAll(
            'SELECT a.*, vi.Title as ItemTitle
             FROM AUDIT_LOG a
             LEFT JOIN VAULT_ITEM vi ON a.ItemID = vi.ItemID
             WHERE a.UserID = ?
             ORDER BY a.CreatedAt DESC
             LIMIT ?',
            [$userId, $limit]
        );
    }
}
