<?php

return [
    'db' => [
        'host' => $_ENV['DB_HOST'] ?? 'localhost',
        'port' => $_ENV['DB_PORT'] ?? '3306',
        'name' => $_ENV['DB_NAME'] ?? 'password_manager',
        'user' => $_ENV['DB_USER'] ?? 'root',
        'pass' => $_ENV['DB_PASS'] ?? '',
    ],
    'app' => [
        'name' => 'Password Manager',
        'session_name' => 'pm_session',
        'session_lifetime' => 86400,
        'csrf_token_name' => 'csrf_token',
        'rate_limit_requests' => 100,
        'rate_limit_window' => 60,
    ],
];
