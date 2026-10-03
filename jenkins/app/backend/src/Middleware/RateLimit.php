<?php

class RateLimit
{
    private const MAX_REQUESTS = 100;
    private const WINDOW = 60;

    public static function check(string $key): void
    {
        $now = time();
        $windowStart = $now - self::WINDOW;

        if (!isset($_SESSION['rate_limit'])) {
            $_SESSION['rate_limit'] = [];
        }

        $_SESSION['rate_limit'][$key] = array_filter(
            $_SESSION['rate_limit'][$key] ?? [],
            fn($t) => $t > $windowStart
        );

        if (count($_SESSION['rate_limit'][$key]) >= self::MAX_REQUESTS) {
            Response::error('Rate limit exceeded', 429);
        }

        $_SESSION['rate_limit'][$key][] = $now;
    }
}
