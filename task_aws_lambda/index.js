exports.handler = async (event) => {
  try {
    const body = JSON.parse(event.body || "{}");
    const userMessage = body.message;

    if (!userMessage) {
      return response(400, { error: "Message is required" });
    }

    const messages = body.messages || [
      {
        role: "user",
        content: userMessage
      }
    ];

    const nimResponse = await fetch(
      "https://integrate.api.nvidia.com/v1/chat/completions",
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${process.env.NVIDIA_API_KEY}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          model: "meta/llama-3.1-8b-instruct",
          messages,
          temperature: 0.7,
          max_tokens: 512,
          stream: false
        })
      }
    );

    const result = await nimResponse.json();

if (!nimResponse.ok) {
  console.error("NVIDIA status:", nimResponse.status);
  console.error("NVIDIA response:", result);

  return response(nimResponse.status, {
    error: "NVIDIA NIM request failed",
    nvidiaStatus: nimResponse.status,
    nvidiaResponse: result
  });
}


    const reply = result.choices?.[0]?.message?.content || "No response";

    return response(200, {
      reply
    });
  } catch (error) {
    console.error(error);

    return response(500, {
      error: "Server error",
      details: error.message
    });
  }
};

function response(statusCode, body) {
  return {
    statusCode,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "content-type",
      "Access-Control-Allow-Methods": "POST, OPTIONS"
    },
    body: JSON.stringify(body)
  };
}
