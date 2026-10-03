<?php

class AuthController
{
    public static function register(Request $request): void
    {
        $username = trim($request->input('username', ''));
        $email = trim($request->input('email', ''));
        $password = $request->input('password', '');

        if (!$username || !$email || !$password) {
            Response::error('Username, email and password are required');
        }
        if (strlen($password) < 8) {
            Response::error('Password must be at least 8 characters');
        }
        if (UserRepo::findByUsername($username)) {
            Response::error('Username already taken', 409);
        }
        if (UserRepo::findByEmail($email)) {
            Response::error('Email already registered', 409);
        }

        $hash = password_hash($password, PASSWORD_ARGON2ID);
        $userId = UserRepo::create($username, $email, $hash);

        $user = UserRepo::findById($userId);
        Auth::login($user);
        AuditRepo::log($userId, null, 'REGISTERED');

        Response::json([
            'user' => self::sanitize($user),
            'token' => $_SESSION['token'],
            'csrf_token' => Csrf::token(),
        ], 201);
    }

    public static function login(Request $request): void
    {
        $username = trim($request->input('username', ''));
        $password = $request->input('password', '');

        if (!$username || !$password) {
            Response::error('Username and password are required');
        }

        $user = UserRepo::findByUsername($username);
        if (!$user || !password_verify($password, $user['PasswordHash'])) {
            Response::unauthorized('Invalid credentials');
        }

        Auth::login($user);
        AuditRepo::log((int)$user['UserID'], null, 'LOGIN');

        Response::json([
            'user' => self::sanitize($user),
            'token' => $_SESSION['token'],
            'csrf_token' => Csrf::token(),
        ]);
    }

    public static function logout(Request $request): void
    {
        $user = Auth::user();
        if ($user) {
            Auth::logout();
            AuditRepo::log((int)$user['UserID'], null, 'LOGOUT');
        }
        Response::json(['message' => 'Logged out']);
    }

    public static function me(Request $request): void
    {
        $user = Auth::require();
        Response::json(['user' => self::sanitize($user)]);
    }

    private static function sanitize(array $user): array
    {
        return [
            'id' => (int)$user['UserID'],
            'username' => $user['Username'],
            'email' => $user['Email'],
            'createdAt' => $user['CreatedAt'],
        ];
    }
}
