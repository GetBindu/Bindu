using Bindu.Grpc;
using System.Net;
using System.Net.Sockets;
using System.Text.Json;

namespace Bindu.Sdk.Tests;

public class BinduAgentBindufyTests {
    private static AgentConfig TestConfig() => new() {
        Author = "dev@example.com",
        Name = "flow-agent",
        Description = "Agent exercising the full Bindufy flow",
        GrpcCallbackPort = 0,
        Version = "3.2.1"
    };

    private static Task<object> TestHandler(IReadOnlyList<ChatMessage> messages) =>
        Task.FromResult<object>($"Echo: {messages[^1].Content}");

    private static int FreePort() {
        var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        var port = ((IPEndPoint)listener.LocalEndpoint).Port;
        listener.Stop();
        return port;
    }

    [Fact]
    public async Task Bindufy_Registers_And_Returns_Registration_Result() {
        await using var core = await FakeBinduCore.StartAsync();
        using var bindu = new BinduAgent(new NoOpCoreLauncher(), core.Address);

        var result = await bindu.Bindufy(TestConfig(), TestHandler);

        Assert.Equal("agent-0001", result.AgentId);
        Assert.Equal("did:bindu:test", result.Did);
        Assert.Equal("http://localhost:3773", result.AgentUrl);

        // The fake core must have received a well-formed registration.
        var request = core.LastRegisterRequest;
        Assert.NotNull(request);
        Assert.Matches(@"^localhost:\d+$", request!.GrpcCallbackAddress);

        using var doc = JsonDocument.Parse(request.ConfigJson);
        var root = doc.RootElement;
        Assert.Equal("flow-agent", root.GetProperty("name").GetString());
        Assert.Equal("agent", root.GetProperty("kind").GetString());
    }

    [Fact]
    public async Task Bindufy_Throws_When_Core_Rejects_Registration() {
        await using var core = await FakeBinduCore.StartAsync();
        core.RegisterSucceeds = false;
        core.RegisterError = "duplicate agent name";

        using var bindu = new BinduAgent(new NoOpCoreLauncher(), core.Address);

        var ex = await Assert.ThrowsAsync<InvalidOperationException>(() => bindu.Bindufy(TestConfig(), TestHandler));
        Assert.Contains("duplicate agent name", ex.Message);

        // The fake core records the registration request even when it rejects it, so we can
        // learn which callback port BinduAgent had bound. That server must have been stopped
        // when BinduAgent's DisposeAsync cleanup ran on the failed Bindufy attempt, freeing
        // the port for reuse (even though _grpcServer/_grpcClient are private fields).
        var callbackAddress = core.LastRegisterRequest?.GrpcCallbackAddress;
        Assert.NotNull(callbackAddress);
        Assert.Matches(@"^localhost:\d+$", callbackAddress!);

        var callbackPort = int.Parse(callbackAddress!.Split(':')[1]);
        using (var rebind = new TcpListener(IPAddress.Loopback, callbackPort)) {
            rebind.Start(); // Throws if the failed registration's callback port is still bound.
        }
    }

    [Fact]
    public async Task Dispose_Unregisters_Agent_With_The_Core() {
        await using var core = await FakeBinduCore.StartAsync();
        var bindu = new BinduAgent(new NoOpCoreLauncher(), core.Address);

        var result = await bindu.Bindufy(TestConfig(), TestHandler);

        bindu.Dispose();

        Assert.Equal("agent-0001", core.LastUnregisterRequest?.AgentId);
    }

    [Fact]
    public async Task Bindufy_Connects_To_Configured_Core_Grpc_Port() {
        var port = FreePort();
        await using var core = await FakeBinduCore.StartAsync(port);

        var config = TestConfig();
        config.CoreGrpcPort = port;

        // No core address is injected — Bindufy must derive the client address from
        // config.CoreGrpcPort and launch the core on the same (non-default) port.
        using var bindu = new BinduAgent(new NoOpCoreLauncher(config.CoreGrpcPort));

        var result = await bindu.Bindufy(config, TestHandler);

        Assert.Equal("agent-0001", result.AgentId);
        Assert.Equal(port, core.Port);
        Assert.NotNull(core.LastRegisterRequest);
    }

    [Fact]
    public async Task Dispose_Async_Unregisters_Agent_With_The_Core() {
        await using var core = await FakeBinduCore.StartAsync();
        await using var bindu = new BinduAgent(new NoOpCoreLauncher(), core.Address);

        var result = await bindu.Bindufy(TestConfig(), TestHandler);
        await bindu.DisposeAsync();

        Assert.Equal("agent-0001", core.LastUnregisterRequest?.AgentId);
    }
}
