<?php

class VaultRepo
{
    public static function findById(int $id): ?array
    {
        return Db::fetch('SELECT * FROM VAULT WHERE VaultID = ?', [$id]);
    }

    public static function findByUser(int $userId): array
    {
        return Db::fetchAll('SELECT * FROM VAULT WHERE UserID = ? ORDER BY CreatedAt DESC', [$userId]);
    }

    public static function create(int $userId, string $name): int
    {
        return Db::insert('INSERT INTO VAULT (UserID, VaultName) VALUES (?, ?)', [$userId, $name]);
    }

    public static function update(int $id, string $name): void
    {
        Db::execute('UPDATE VAULT SET VaultName = ? WHERE VaultID = ?', [$name, $id]);
    }

    public static function delete(int $id): void
    {
        Db::execute('DELETE FROM VAULT WHERE VaultID = ?', [$id]);
    }

    public static function belongsToUser(int $vaultId, int $userId): bool
    {
        $vault = self::findById($vaultId);
        return $vault && (int)$vault['UserID'] === $userId;
    }
}
