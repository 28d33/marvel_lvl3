<?php

class Auth
{
    public static function user(): ?array
    {
        if (isset($_SESSION['user_id'])) {
            return UserRepo::findById($_SESSION['user_id']);
        }

        $token = (new Request())->bearerToken();
        if ($token) {
            $user = UserRepo::findByToken($token);
            if ($user) {
                $_SESSION['user_id'] = $user['UserID'];
                return $user;
            }
        }

        return null;
    }

    public static function require(): array
    {
        $user = self::user();
        if (!$user) {
            Response::unauthorized();
        }
        return $user;
    }

    public static function login(array $user): void
    {
        $_SESSION['user_id'] = $user['UserID'];
        $_SESSION['token'] = bin2hex(random_bytes(32));
        try {
            UserRepo::setToken($user['UserID'], $_SESSION['token']);
        } catch (\Exception $e) {
            // Token column may not exist in older schema
        }
    }

    public static function logout(): void
    {
        if (isset($_SESSION['user_id'])) {
            try {
                UserRepo::clearToken($_SESSION['user_id']);
            } catch (\Exception $e) {
                // Token column may not exist in older schema
            }
        }
        session_destroy();
    }
}
