<?php

class VaultService
{
    public static function list(int $userId): array
    {
        return VaultRepo::findByUser($userId);
    }

    public static function create(int $userId, string $name): array
    {
        $id = VaultRepo::create($userId, $name);
        return VaultRepo::findById($id);
    }

    public static function update(int $vaultId, int $userId, string $name): array
    {
        if (!VaultRepo::belongsToUser($vaultId, $userId)) {
            Response::forbidden();
        }
        VaultRepo::update($vaultId, $name);
        return VaultRepo::findById($vaultId);
    }

    public static function delete(int $vaultId, int $userId): void
    {
        if (!VaultRepo::belongsToUser($vaultId, $userId)) {
            Response::forbidden();
        }
        VaultRepo::delete($vaultId);
    }
}
