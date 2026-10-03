<?php

class VaultController
{
    public static function index(Request $request): void
    {
        $user = Auth::require();
        Response::json(['vaults' => VaultService::list((int)$user['UserID'])]);
    }

    public static function store(Request $request): void
    {
        $user = Auth::require();
        $name = trim($request->input('name', ''));
        if (!$name) Response::error('Vault name is required');

        $vault = VaultService::create((int)$user['UserID'], $name);
        Response::json(['vault' => $vault], 201);
    }

    public static function update(Request $request): void
    {
        $user = Auth::require();
        $name = trim($request->input('name', ''));
        if (!$name) Response::error('Vault name is required');

        $vault = VaultService::update((int)$request->input('id'), (int)$user['UserID'], $name);
        Response::json(['vault' => $vault]);
    }

    public static function destroy(Request $request): void
    {
        $user = Auth::require();
        VaultService::delete((int)$request->input('id'), (int)$user['UserID']);
        Response::noContent();
    }
}
