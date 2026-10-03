<?php

class MethodOverride
{
    public static function handle(Request $request): void
    {
        $override = $_POST['_method'] ?? $_SERVER['HTTP_X_HTTP_METHOD_OVERRIDE'] ?? null;
        if ($override && $request->method() === 'POST') {
            $_SERVER['REQUEST_METHOD'] = strtoupper($override);
        }
    }
}
