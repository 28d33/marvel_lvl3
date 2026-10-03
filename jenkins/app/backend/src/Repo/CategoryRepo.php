<?php

class CategoryRepo
{
    public static function findById(int $id): ?array
    {
        return Db::fetch('SELECT * FROM CATEGORY WHERE CategoryID = ?', [$id]);
    }

    public static function findByUser(int $userId): array
    {
        return Db::fetchAll('SELECT * FROM CATEGORY WHERE UserID = ? ORDER BY CategoryName', [$userId]);
    }

    public static function create(int $userId, string $name): int
    {
        return Db::insert('INSERT INTO CATEGORY (UserID, CategoryName) VALUES (?, ?)', [$userId, $name]);
    }

    public static function delete(int $id): void
    {
        Db::execute('DELETE FROM CATEGORY WHERE CategoryID = ?', [$id]);
    }

    public static function attachToItem(int $itemId, int $categoryId): void
    {
        Db::execute(
            'INSERT IGNORE INTO ITEM_CATEGORY (ItemID, CategoryID) VALUES (?, ?)',
            [$itemId, $categoryId]
        );
    }

    public static function detachFromItem(int $itemId, int $categoryId): void
    {
        Db::execute('DELETE FROM ITEM_CATEGORY WHERE ItemID = ? AND CategoryID = ?', [$itemId, $categoryId]);
    }

    public static function getItemCategories(int $itemId): array
    {
        return Db::fetchAll(
            'SELECT c.* FROM CATEGORY c
             JOIN ITEM_CATEGORY ic ON c.CategoryID = ic.CategoryID
             WHERE ic.ItemID = ? ORDER BY c.CategoryName',
            [$itemId]
        );
    }
}
