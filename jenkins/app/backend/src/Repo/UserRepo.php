<?php

class UserRepo
{
    public static function findById(int $id): ?array
    {
        return Db::fetch('SELECT * FROM USER WHERE UserID = ?', [$id]);
    }

    public static function findByUsername(string $username): ?array
    {
        return Db::fetch('SELECT * FROM USER WHERE Username = ?', [$username]);
    }

    public static function findByEmail(string $email): ?array
    {
        return Db::fetch('SELECT * FROM USER WHERE Email = ?', [$email]);
    }

    public static function findByToken(string $token): ?array
    {
        return Db::fetch('SELECT * FROM USER WHERE Token = ?', [$token]);
    }

    public static function create(string $username, string $email, string $passwordHash): int
    {
        return Db::insert(
            'INSERT INTO USER (Username, Email, PasswordHash) VALUES (?, ?, ?)',
            [$username, $email, $passwordHash]
        );
    }

    public static function setToken(int $userId, string $token): void
    {
        Db::execute('UPDATE USER SET Token = ? WHERE UserID = ?', [$token, $userId]);
    }

    public static function clearToken(int $userId): void
    {
        Db::execute('UPDATE USER SET Token = NULL WHERE UserID = ?', [$userId]);
    }
}
