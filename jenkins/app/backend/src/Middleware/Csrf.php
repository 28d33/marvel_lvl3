<?php

class Csrf
{
    public static function token(): string
    {
        if (empty($_SESSION['csrf_token'])) {
            $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
        }
        return $_SESSION['csrf_token'];
    }

    public static function validate(Request $request): void
    {
        if (in_array($request->method(), ['POST', 'PUT', 'DELETE'])) {
            $header = $request->header('X-CSRF-Token');
            $body = $request->input('csrf_token');
            $token = $header ?: $body;

            if (!$token || !hash_equals(self::token(), $token)) {
                Response::forbidden('Invalid CSRF token');
            }
        }
    }
}
