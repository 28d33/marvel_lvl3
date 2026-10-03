<?php

class ItemController
{
    public static function index(Request $request): void
    {
        $user = Auth::require();
        $items = ItemService::list((int)$request->input('vaultId'), (int)$user['UserID']);
        Response::json(['items' => $items]);
    }

    public static function show(Request $request): void
    {
        $user = Auth::require();
        $item = ItemService::get((int)$request->input('id'), (int)$user['UserID']);
        AuditRepo::log((int)$user['UserID'], (int)$item['ItemID'], 'READ');
        Response::json(['item' => $item]);
    }

    public static function store(Request $request): void
    {
        $user = Auth::require();
        $vaultId = (int)$request->input('vaultId');
        $title = trim($request->input('title', ''));
        $type = $request->input('type', '');

        if (!$title) Response::error('Title is required');
        if (!in_array($type, ['PASSWORD', 'TOTP', 'PASSKEY', 'SECURE_NOTE'])) {
            Response::error('Invalid item type');
        }

        $data = self::extractTypeData($request, $type);
        $item = ItemService::create($vaultId, (int)$user['UserID'], $title, $type, $data);
        Response::json(['item' => $item], 201);
    }

    public static function update(Request $request): void
    {
        $user = Auth::require();
        $title = trim($request->input('title', ''));
        if (!$title) Response::error('Title is required');

        $item = ItemRepo::findById((int)$request->input('id'));
        if (!$item) Response::notFound();

        $data = self::extractTypeData($request, $item['ItemType']);
        $updated = ItemService::update((int)$request->input('id'), (int)$user['UserID'], $title, $data);
        Response::json(['item' => $updated]);
    }

    public static function destroy(Request $request): void
    {
        $user = Auth::require();
        ItemService::delete((int)$request->input('id'), (int)$user['UserID']);
        Response::noContent();
    }

    private static function extractTypeData(Request $request, string $type): array
    {
        return match ($type) {
            'PASSWORD' => [
                'username' => $request->input('username', ''),
                'password' => $request->input('password', ''),
                'url' => $request->input('url', ''),
            ],
            'TOTP' => [
                'secret' => $request->input('secret', ''),
                'issuer' => $request->input('issuer', ''),
                'account' => $request->input('account', ''),
            ],
            'PASSKEY' => [
                'rpId' => $request->input('rpId', ''),
                'credentialId' => $request->input('credentialId', ''),
                'privateKey' => $request->input('privateKey', ''),
            ],
            'SECURE_NOTE' => [
                'content' => $request->input('content', ''),
            ],
            default => [],
        };
    }
}
