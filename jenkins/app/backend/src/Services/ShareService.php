<?php

class ShareService
{
    public static function share(int $itemId, int $userId, string $targetUsername, string $permission): array
    {
        $item = ItemRepo::findById($itemId);
        if (!$item) Response::notFound('Item not found');

        $vault = VaultRepo::findById($item['VaultID']);
        if (!$vault || (int)$vault['UserID'] !== $userId) {
            Response::forbidden();
        }

        $target = UserRepo::findByUsername($targetUsername);
        if (!$target) Response::notFound('User not found');

        $existing = ShareRepo::findByItemAndUser($itemId, (int)$target['UserID']);
        if ($existing) {
            ShareRepo::update($existing['ShareID'], $permission);
            return ShareRepo::findById($existing['ShareID']);
        }

        $id = ShareRepo::create($itemId, $userId, (int)$target['UserID'], $permission);
        AuditRepo::log($userId, $itemId, 'SHARED');
        return ShareRepo::findById($id);
    }

    public static function list(int $userId): array
    {
        return ShareRepo::findByUser($userId);
    }

    public static function update(int $shareId, int $userId, string $permission): array
    {
        $share = ShareRepo::findById($shareId);
        if (!$share) Response::notFound('Share not found');

        $item = ItemRepo::findById($share['ItemID']);
        $vault = VaultRepo::findById($item['VaultID']);
        if (!$vault || (int)$vault['UserID'] !== $userId) {
            Response::forbidden();
        }

        ShareRepo::update($shareId, $permission);
        return ShareRepo::findById($shareId);
    }

    public static function revoke(int $shareId, int $userId): void
    {
        $share = ShareRepo::findById($shareId);
        if (!$share) Response::notFound('Share not found');

        $item = ItemRepo::findById($share['ItemID']);
        $vault = VaultRepo::findById($item['VaultID']);
        if (!$vault || (int)$vault['UserID'] !== $userId) {
            Response::forbidden();
        }

        ShareRepo::delete($shareId);
        AuditRepo::log($userId, $share['ItemID'], 'REVOKED');
    }
}
