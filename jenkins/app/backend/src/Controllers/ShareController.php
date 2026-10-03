<?php

class ShareController
{
    public static function store(Request $request): void
    {
        $user = Auth::require();
        $itemId = (int)$request->input('itemId');
        $targetUsername = trim($request->input('username', ''));
        $permission = $request->input('permission', 'READ');

        if (!$targetUsername) Response::error('Target username is required');
        if (!in_array($permission, ['READ', 'READ_WRITE'])) {
            Response::error('Invalid permission');
        }

        $share = ShareService::share($itemId, (int)$user['UserID'], $targetUsername, $permission);
        Response::json(['share' => $share], 201);
    }

    public static function index(Request $request): void
    {
        $user = Auth::require();
        Response::json(['shares' => ShareService::list((int)$user['UserID'])]);
    }

    public static function update(Request $request): void
    {
        $user = Auth::require();
        $permission = $request->input('permission', 'READ');
        if (!in_array($permission, ['READ', 'READ_WRITE'])) {
            Response::error('Invalid permission');
        }

        $share = ShareService::update((int)$request->input('id'), (int)$user['UserID'], $permission);
        Response::json(['share' => $share]);
    }

    public static function destroy(Request $request): void
    {
        $user = Auth::require();
        ShareService::revoke((int)$request->input('id'), (int)$user['UserID']);
        Response::noContent();
    }
}
