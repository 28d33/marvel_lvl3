<?php

class AttachmentController
{
    public static function store(Request $request): void
    {
        $user = Auth::require();
        $itemId = (int)$request->input('itemId');

        $item = ItemRepo::findById($itemId);
        if (!$item) Response::notFound('Item not found');

        if (!isset($_FILES['file'])) {
            Response::error('No file uploaded');
        }

        $file = $_FILES['file'];
        $id = AttachmentRepo::create($itemId, $file['name'], $file['type'], $file['size']);

        $chunkSize = 65536;
        $chunkNo = 0;
        $handle = fopen($file['tmp_name'], 'rb');
        while (!feof($handle)) {
            $chunk = fread($handle, $chunkSize);
            AttachmentRepo::addChunk($id, $chunkNo++, $chunk);
        }
        fclose($handle);

        AuditRepo::log((int)$user['UserID'], $itemId, 'ATTACHMENT_UPLOADED');
        Response::json(['attachment' => AttachmentRepo::findById($id)], 201);
    }

    public static function show(Request $request): void
    {
        $user = Auth::require();
        $attachment = AttachmentRepo::findById((int)$request->input('id'));
        if (!$attachment) Response::notFound();

        $item = ItemRepo::findById($attachment['ItemID']);
        $vault = VaultRepo::findById($item['VaultID']);
        if (!$vault || (int)$vault['UserID'] !== (int)$user['UserID']) {
            Response::forbidden();
        }

        Response::json(['attachment' => $attachment]);
    }

    public static function storeChunk(Request $request): void
    {
        $user = Auth::require();
        $attachmentId = (int)$request->input('id');
        $chunkNo = (int)$request->input('no');

        $attachment = AttachmentRepo::findById($attachmentId);
        if (!$attachment) Response::notFound();

        $data = file_get_contents('php://input');
        AttachmentRepo::addChunk($attachmentId, $chunkNo, $data);

        Response::json(['chunk' => $chunkNo, 'stored' => true]);
    }

    public static function showChunk(Request $request): void
    {
        $user = Auth::require();
        $attachmentId = (int)$request->input('id');
        $chunkNo = (int)$request->input('no');

        $chunk = AttachmentRepo::getChunk($attachmentId, $chunkNo);
        if (!$chunk) Response::notFound('Chunk not found');

        header('Content-Type: application/octet-stream');
        echo $chunk['EncryptedData'];
        exit;
    }

    public static function listChunks(Request $request): void
    {
        $user = Auth::require();
        $attachmentId = (int)$request->input('id');

        $attachment = AttachmentRepo::findById($attachmentId);
        if (!$attachment) Response::notFound();

        $chunks = AttachmentRepo::getChunks($attachmentId);
        Response::json(['chunks' => $chunks, 'total' => count($chunks)]);
    }
}
