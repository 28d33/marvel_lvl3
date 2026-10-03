<?php

class AuditService
{
    public static function log(int $userId, ?int $itemId, string $action): void
    {
        AuditRepo::log($userId, $itemId, $action);
    }

    public static function list(int $userId): array
    {
        return AuditRepo::findByUser($userId);
    }
}
