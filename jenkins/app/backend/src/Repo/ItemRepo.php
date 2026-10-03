<?php

class ItemRepo
{
    public static function findById(int $id): ?array
    {
        return Db::fetch('SELECT * FROM VAULT_ITEM WHERE ItemID = ?', [$id]);
    }

    public static function findByVault(int $vaultId): array
    {
        return Db::fetchAll('SELECT * FROM VAULT_ITEM WHERE VaultID = ? ORDER BY CreatedAt DESC', [$vaultId]);
    }

    public static function create(int $vaultId, string $title, string $type): int
    {
        return Db::insert(
            'INSERT INTO VAULT_ITEM (VaultID, Title, ItemType) VALUES (?, ?, ?)',
            [$vaultId, $title, $type]
        );
    }

    public static function update(int $id, string $title): void
    {
        Db::execute('UPDATE VAULT_ITEM SET Title = ? WHERE ItemID = ?', [$title, $id]);
    }

    public static function delete(int $id): void
    {
        Db::execute('DELETE FROM VAULT_ITEM WHERE ItemID = ?', [$id]);
    }

    public static function getTypeData(int $id, string $type): ?array
    {
        $table = match ($type) {
            'PASSWORD' => 'PASSWORD',
            'TOTP' => 'TOTP',
            'PASSKEY' => 'PASSKEY',
            'SECURE_NOTE' => 'SECURE_NOTE',
            default => null,
        };
        if (!$table) return null;
        return Db::fetch("SELECT * FROM {$table} WHERE ItemID = ?", [$id]);
    }

    public static function setTypeData(int $id, string $type, array $data): void
    {
        switch ($type) {
            case 'PASSWORD':
                Db::execute(
                    'INSERT INTO PASSWORD (ItemID, UsernameEnc, PasswordEnc, UrlEnc) VALUES (?, ?, ?, ?)
                     ON DUPLICATE KEY UPDATE UsernameEnc=VALUES(UsernameEnc), PasswordEnc=VALUES(PasswordEnc), UrlEnc=VALUES(UrlEnc)',
                    [$id, $data['username'], $data['password'], $data['url']]
                );
                break;
            case 'TOTP':
                Db::execute(
                    'INSERT INTO TOTP (ItemID, SecretEnc, Issuer, AccountName) VALUES (?, ?, ?, ?)
                     ON DUPLICATE KEY UPDATE SecretEnc=VALUES(SecretEnc), Issuer=VALUES(Issuer), AccountName=VALUES(AccountName)',
                    [$id, $data['secret'], $data['issuer'], $data['account']]
                );
                break;
            case 'PASSKEY':
                Db::execute(
                    'INSERT INTO PASSKEY (ItemID, RpId, CredentialId, PrivateKeyEnc) VALUES (?, ?, ?, ?)
                     ON DUPLICATE KEY UPDATE RpId=VALUES(RpId), CredentialId=VALUES(CredentialId), PrivateKeyEnc=VALUES(PrivateKeyEnc)',
                    [$id, $data['rpId'], $data['credentialId'], $data['privateKey']]
                );
                break;
            case 'SECURE_NOTE':
                Db::execute(
                    'INSERT INTO SECURE_NOTE (ItemID, ContentEnc) VALUES (?, ?)
                     ON DUPLICATE KEY UPDATE ContentEnc=VALUES(ContentEnc)',
                    [$id, $data['content']]
                );
                break;
        }
    }

    public static function deleteTypeData(int $id, string $type): void
    {
        $table = match ($type) {
            'PASSWORD' => 'PASSWORD',
            'TOTP' => 'TOTP',
            'PASSKEY' => 'PASSKEY',
            'SECURE_NOTE' => 'SECURE_NOTE',
            default => null,
        };
        if ($table) {
            Db::execute("DELETE FROM {$table} WHERE ItemID = ?", [$id]);
        }
    }
}
