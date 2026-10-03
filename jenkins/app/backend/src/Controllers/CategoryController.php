<?php

class CategoryController
{
    public static function index(Request $request): void
    {
        $user = Auth::require();
        Response::json(['categories' => CategoryRepo::findByUser((int)$user['UserID'])]);
    }

    public static function store(Request $request): void
    {
        $user = Auth::require();
        $name = trim($request->input('name', ''));
        if (!$name) Response::error('Category name is required');

        $id = CategoryRepo::create((int)$user['UserID'], $name);
        Response::json(['category' => CategoryRepo::findById($id)], 201);
    }

    public static function attach(Request $request): void
    {
        $user = Auth::require();
        $itemId = (int)$request->input('itemId');
        $categoryId = (int)$request->input('categoryId');

        $item = ItemRepo::findById($itemId);
        if (!$item) Response::notFound('Item not found');

        $vault = VaultRepo::findById($item['VaultID']);
        if (!$vault || (int)$vault['UserID'] !== (int)$user['UserID']) {
            Response::forbidden();
        }

        $category = CategoryRepo::findById($categoryId);
        if (!$category || (int)$category['UserID'] !== (int)$user['UserID']) {
            Response::forbidden();
        }

        CategoryRepo::attachToItem($itemId, $categoryId);
        Response::json(['attached' => true]);
    }

    public static function detach(Request $request): void
    {
        $user = Auth::require();
        $itemId = (int)$request->input('itemId');
        $categoryId = (int)$request->input('categoryId');

        CategoryRepo::detachFromItem($itemId, $categoryId);
        Response::json(['detached' => true]);
    }
}
