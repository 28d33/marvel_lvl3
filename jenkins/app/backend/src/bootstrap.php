<?php

spl_autoload_register(function ($class) {
    $file = __DIR__ . '/' . $class . '.php';
    if (file_exists($file)) {
        require $file;
        return;
    }
    $file = __DIR__ . '/Controllers/' . $class . '.php';
    if (file_exists($file)) {
        require $file;
        return;
    }
    $file = __DIR__ . '/Services/' . $class . '.php';
    if (file_exists($file)) {
        require $file;
        return;
    }
    $file = __DIR__ . '/Repo/' . $class . '.php';
    if (file_exists($file)) {
        require $file;
        return;
    }
    $file = __DIR__ . '/Middleware/' . $class . '.php';
    if (file_exists($file)) {
        require $file;
    }
});

Config::load(__DIR__ . '/../config.php');

session_name(Config::get('app.session_name', 'pm_session'));
session_start();
