<?php

class Router
{
    private array $routes = [];
    private array $patterns = [
        '{id}' => '(\d+)',
        '{vaultId}' => '(\d+)',
        '{itemId}' => '(\d+)',
        '{categoryId}' => '(\d+)',
        '{no}' => '(\d+)',
    ];

    public function add(string $method, string $path, array|Closure $handler): void
    {
        $this->routes[] = ['method' => $method, 'path' => $path, 'handler' => $handler];
    }

    public function dispatch(Request $request): void
    {
        $method = $request->method();
        $path = $request->path();

        foreach ($this->routes as $route) {
            if ($route['method'] !== $method) {
                continue;
            }

            $pattern = $this->compile($route['path']);
            if (preg_match($pattern, $path, $matches)) {
                array_shift($matches);
                $params = [];
                preg_match_all('/\{(\w+)\}/', $route['path'], $names);
                foreach ($names[1] as $i => $name) {
                    $params[$name] = $matches[$i] ?? null;
                    $request->setParam($name, $params[$name]);
                }
                call_user_func($route['handler'], $request);
                return;
            }
        }

        Response::notFound('Route not found');
    }

    private function compile(string $path): string
    {
        $pattern = preg_replace_callback('/\{(\w+)\}/', function ($m) {
            return $this->patterns['{' . $m[1] . '}'] ?? '([^/]+)';
        }, $path);
        return '#^' . $pattern . '$#';
    }
}
