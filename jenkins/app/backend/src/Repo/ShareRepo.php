<?php

class ShareRepo
{
    public static function findById(int $id): ?array
    {
        return Db::fetch('SELECT * FROM SHARE WHERE ShareID = ?', [$id]);
    }

    public static function findByUser(int $userId): array
    {
        return Db::fetchAll(
            'SELECT s.*, vi.Title as ItemTitle, u.Username as SharedByName
             FROM SHARE s
             JOIN VAULT_ITEM vi ON s.ItemID = vi.ItemID
             JOIN USER u ON s.SharedBy = u.UserID
             WHERE s.SharedWith = ? ORDER BY s.CreatedAt DESC',
            [$userId]
        );
    }

    public static function create(int $itemId, int $sharedBy, int $sharedWith, string $permission): int
    {
        return Db::insert(
            'INSERT INTO SHARE (ItemID, SharedBy, SharedWith, Permission) VALUES (?, ?, ?, ?)',
            [$itemId, $sharedBy, $sharedWith, $permission]
        );
    }

    public static function update(int $id, string $permission): void
    {
        Db::execute('UPDATE SHARE SET Permission = ? WHERE ShareID = ?', [$permission, $id]);
    }

    public static function delete(int $id): void
    {
        Db::execute('DELETE FROM SHARE WHERE ShareID = ?', [$id]);
    }

    public static function findByItemAndUser(int $itemId, int $userId): ?array
    {
        return Db::fetch(
            'SELECT * FROM SHARE WHERE ItemID = ? AND SharedWith = ?',
            [$itemId, $userId]
        );
    }
}
