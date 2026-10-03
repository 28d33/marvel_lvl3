<?php

class Request
{
    private string $method;
    private string $path;
    private array $params;
    private array $body;
    private array $headers;

    public function __construct()
    {
        $this->method = strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET');
        $this->path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);
        $this->headers = getallheaders() ?: [];

        $override = $this->headers['X-HTTP-Method-Override'] ?? null;
        if ($override) {
            $this->method = strtoupper($override);
        }

        $input = file_get_contents('php://input');
        $this->body = json_decode($input, true) ?? [];
        if (empty($this->body)) {
            parse_str($input, $this->body);
        }
        $this->params = array_merge($_GET, $_POST);
    }

    public function method(): string
    {
        return $this->method;
    }

    public function path(): string
    {
        return rtrim($this->path, '/') ?: '/';
    }

    public function input(string $key, $default = null)
    {
        return $this->body[$key] ?? $this->params[$key] ?? $default;
    }

    public function all(): array
    {
        return array_merge($this->params, $this->body);
    }

    public function header(string $key, $default = null)
    {
        return $this->headers[$key] ?? $default;
    }

    public function bearerToken(): ?string
    {
        $auth = $this->header('Authorization', '');
        if (preg_match('/Bearer\s+(\S+)/', $auth, $m)) {
            return $m[1];
        }
        return null;
    }

    public function setParam(string $key, $value): void
    {
        $this->params[$key] = $value;
    }
}
