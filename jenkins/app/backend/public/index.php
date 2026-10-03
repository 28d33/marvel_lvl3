<?php

require __DIR__ . '/../src/bootstrap.php';

$router = new Router();

$router->add('POST', '/api/auth/register', [AuthController::class, 'register']);
$router->add('POST', '/api/auth/login', [AuthController::class, 'login']);
$router->add('POST', '/api/auth/logout', [AuthController::class, 'logout']);
$router->add('GET', '/api/auth/me', [AuthController::class, 'me']);

$router->add('GET', '/api/vaults', [VaultController::class, 'index']);
$router->add('POST', '/api/vaults', [VaultController::class, 'store']);
$router->add('PUT', '/api/vaults/{id}', [VaultController::class, 'update']);
$router->add('DELETE', '/api/vaults/{id}', [VaultController::class, 'destroy']);

$router->add('GET', '/api/vaults/{vaultId}/items', [ItemController::class, 'index']);
$router->add('POST', '/api/vaults/{vaultId}/items', [ItemController::class, 'store']);
$router->add('GET', '/api/items/{id}', [ItemController::class, 'show']);
$router->add('PUT', '/api/items/{id}', [ItemController::class, 'update']);
$router->add('DELETE', '/api/items/{id}', [ItemController::class, 'destroy']);

$router->add('POST', '/api/items/{itemId}/attachments', [AttachmentController::class, 'store']);
$router->add('GET', '/api/attachments/{id}', [AttachmentController::class, 'show']);
$router->add('PUT', '/api/attachments/{id}/chunks/{no}', [AttachmentController::class, 'storeChunk']);
$router->add('GET', '/api/attachments/{id}/chunks/{no}', [AttachmentController::class, 'showChunk']);
$router->add('GET', '/api/attachments/{id}/chunks', [AttachmentController::class, 'listChunks']);

$router->add('GET', '/api/categories', [CategoryController::class, 'index']);
$router->add('POST', '/api/categories', [CategoryController::class, 'store']);
$router->add('POST', '/api/items/{itemId}/categories', [CategoryController::class, 'attach']);
$router->add('DELETE', '/api/items/{itemId}/categories/{categoryId}', [CategoryController::class, 'detach']);

$router->add('POST', '/api/items/{itemId}/share', [ShareController::class, 'store']);
$router->add('GET', '/api/shares', [ShareController::class, 'index']);
$router->add('PUT', '/api/shares/{id}', [ShareController::class, 'update']);
$router->add('DELETE', '/api/shares/{id}', [ShareController::class, 'destroy']);

$router->add('GET', '/api/audit', function (Request $request) {
    $user = Auth::require();
    Response::json(['audit' => AuditService::list((int)$user['UserID'])]);
});

$request = new Request();
$router->dispatch($request);
