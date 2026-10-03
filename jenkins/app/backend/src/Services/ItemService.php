<?php

class ItemService
{
    public static function list(int $vaultId, int $userId): array
    {
        if (!VaultRepo::belongsToUser($vaultId, $userId)) {
            Response::forbidden();
        }
        $items = ItemRepo::findByVault($vaultId);
        foreach ($items as &$item) {
            $item['typeData'] = ItemRepo::getTypeData($item['ItemID'], $item['ItemType']);
            $item['categories'] = CategoryRepo::getItemCategories($item['ItemID']);
        }
        return $items;
    }

    public static function get(int $itemId, int $userId): array
    {
        $item = ItemRepo::findById($itemId);
        if (!$item) Response::notFound('Item not found');

        $vault = VaultRepo::findById($item['VaultID']);
        if (!$vault || (int)$vault['UserID'] !== $userId) {
            $share = ShareRepo::findByItemAndUser($itemId, $userId);
            if (!$share) Response::forbidden();
        }

        $item['typeData'] = ItemRepo::getTypeData($itemId, $item['ItemType']);
        $item['categories'] = CategoryRepo::getItemCategories($itemId);
        return $item;
    }

    public static function create(int $vaultId, int $userId, string $title, string $type, array $data): array
    {
        if (!VaultRepo::belongsToUser($vaultId, $userId)) {
            Response::forbidden();
        }

        $id = ItemRepo::create($vaultId, $title, $type);
        ItemRepo::setTypeData($id, $type, $data);

        AuditRepo::log($userId, $id, 'CREATED');
        return self::get($id, $userId);
    }

    public static function update(int $itemId, int $userId, string $title, array $data): array
    {
        $item = ItemRepo::findById($itemId);
        if (!$item) Response::notFound('Item not found');

        $vault = VaultRepo::findById($item['VaultID']);
        if (!$vault || (int)$vault['UserID'] !== $userId) {
            $share = ShareRepo::findByItemAndUser($itemId, $userId);
            if (!$share || $share['Permission'] !== 'READ_WRITE') {
                Response::forbidden();
            }
        }

        ItemRepo::update($itemId, $title);
        ItemRepo::setTypeData($itemId, $item['ItemType'], $data);

        AuditRepo::log($userId, $itemId, 'UPDATED');
        return self::get($itemId, $userId);
    }

    public static function delete(int $itemId, int $userId): void
    {
        $item = ItemRepo::findById($itemId);
        if (!$item) Response::notFound('Item not found');

        $vault = VaultRepo::findById($item['VaultID']);
        if (!$vault || (int)$vault['UserID'] !== $userId) {
            Response::forbidden();
        }

        ItemRepo::deleteTypeData($itemId, $item['ItemType']);
        ItemRepo::delete($itemId);
        AuditRepo::log($userId, $itemId, 'DELETED');
    }
}
