using Bindu.Grpc;
using Grpc.Core;
using Grpc.Net.Client;
using System.Net;
using System.Net.Sockets;
using static Bindu.Grpc.AgentHandler;

namespace Bindu.Sdk.Tests;

public class GrpcServerTests {
    private static AgentConfig TestConfig() => new() {
        Author = "dev@example.com",
        Name = "test-agent",
        Description = "Test agent",
        Version = "1.2.3"
    };

    private static int FreePort() {
        var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        var port = ((IPEndPoint)listener.LocalEndpoint).Port;
        listener.Stop();
        return port;
    }

    [Fact]
    public void GetPort_Is_Zero_Before_Start() {
        var server = new GrpcServer(0);
        Assert.Equal(0, server.GetPort);
    }

    [Fact]
    public async Task Port_Zero_Picks_A_Free_Port() {
        var server = new GrpcServer(0);
        await server.StartServerAsync(_ => Task.FromResult<object>("ok"), TestConfig());
        try {
            Assert.True(server.GetPort > 0, "Server should have been assigned an ephemeral port");
        }
        finally {
            await server.StopServerAsync();
        }
    }

    [Fact]
    public async Task Busy_Port_Falls_Back_To_A_Free_Port() {
        var blocker = new TcpListener(IPAddress.Loopback, 0);
        blocker.Start();
        try {
            var busyPort = ((IPEndPoint)blocker.LocalEndpoint).Port;

            var server = new GrpcServer(busyPort);
            await server.StartServerAsync(_ => Task.FromResult<object>("ok"), TestConfig());
            try {
                Assert.NotEqual(busyPort, server.GetPort);
                Assert.True(server.GetPort > 0);
            }
            finally {
                await server.StopServerAsync();
            }
        }
        finally {
            blocker.Stop();
        }
    }

    [Fact]
    public async Task Free_Port_Is_Used_As_Requested() {
        var port = FreePort();

        var server = new GrpcServer(port);
        await server.StartServerAsync(_ => Task.FromResult<object>("ok"), TestConfig());
        try {
            Assert.Equal(port, server.GetPort);
        }
        finally {
            await server.StopServerAsync();
        }
    }

    [Fact]
    public async Task HandleMessages_Round_Trips_Handler_Result() {
        var server = new GrpcServer(0);
        await server.StartServerAsync(
            messages => Task.FromResult<object>($"Echo: {messages[^1].Content}"),
            TestConfig());
        using var channel = GrpcChannel.ForAddress($"http://localhost:{server.GetPort}");
        var client = new AgentHandlerClient(channel);
        try {
            var response = await client.HandleMessagesAsync(new HandleRequest {
                Messages = { new ChatMessage { Role = "user", Content = "hi there" } }
            });

            Assert.Equal("Echo: hi there", response.Content);
            Assert.Equal("", response.State);
            Assert.True(response.IsFinal);
        }
        finally {
            await server.StopServerAsync();
        }
    }

    [Fact]
    public async Task HandleMessages_Maps_BinduResponse_State_Prompt_And_Metadata() {
        var server = new GrpcServer(0);
        await server.StartServerAsync(
            _ => Task.FromResult<object>(new BinduResponse {
                Content = "Need more info",
                State = "input-required",
                Prompt = "Which topic?",
                Metadata = { ["intent"] = "survey" }
            }),
            TestConfig());
        using var channel = GrpcChannel.ForAddress($"http://localhost:{server.GetPort}");
        var client = new AgentHandlerClient(channel);
        try {
            var response = await client.HandleMessagesAsync(new HandleRequest {
                Messages = { new ChatMessage { Role = "user", Content = "start" } }
            });

            Assert.Equal("Need more info", response.Content);
            Assert.Equal("input-required", response.State);
            Assert.Equal("Which topic?", response.Prompt);
            Assert.Equal("survey", response.Metadata["intent"]);
            Assert.True(response.IsFinal);
        }
        finally {
            await server.StopServerAsync();
        }
    }

    [Fact]
    public async Task HandleMessages_Exception_Becomes_Generic_RpcException_Without_Leaking_Details() {
        var server = new GrpcServer(0);
        await server.StartServerAsync(
            _ => throw new InvalidOperationException("handler exploded"),
            TestConfig());
        using var channel = GrpcChannel.ForAddress($"http://localhost:{server.GetPort}");
        var client = new AgentHandlerClient(channel);
        try {
            var ex = await Assert.ThrowsAsync<RpcException>(() =>
                client.HandleMessagesAsync(new HandleRequest {
                    Messages = { new ChatMessage { Role = "user", Content = "boom" } }
                }).ResponseAsync);

            // Security: the internal exception type/message/stack must NOT be exposed to callers.
            Assert.Equal(StatusCode.Internal, ex.StatusCode);
            Assert.Equal("", ex.Status.Detail);
            Assert.DoesNotContain("handler exploded", ex.Status.Detail);
            Assert.Null(ex.Trailers.GetValue("exception-type"));
        }
        finally {
            await server.StopServerAsync();
        }
    }

    [Fact]
    public async Task HandleMessages_Null_Result_Is_Rejected_As_Internal_RpcException() {
        var server = new GrpcServer(0);
        await server.StartServerAsync(_ => Task.FromResult<object>(null!), TestConfig());
        using var channel = GrpcChannel.ForAddress($"http://localhost:{server.GetPort}");
        var client = new AgentHandlerClient(channel);
        try {
            var ex = await Assert.ThrowsAsync<RpcException>(() =>
                client.HandleMessagesAsync(new HandleRequest {
                    Messages = { new ChatMessage { Role = "user", Content = "boom" } }
                }).ResponseAsync);

            Assert.Equal(StatusCode.Internal, ex.StatusCode);
            Assert.Equal("", ex.Status.Detail);
        }
        finally {
            await server.StopServerAsync();
        }
    }

    [Fact]
    public async Task HandleMessages_Unsupported_Result_Type_Is_Rejected_As_Internal_RpcException() {
        var server = new GrpcServer(0);
        await server.StartServerAsync(_ => Task.FromResult<object>(12345), TestConfig());
        using var channel = GrpcChannel.ForAddress($"http://localhost:{server.GetPort}");
        var client = new AgentHandlerClient(channel);
        try {
            var ex = await Assert.ThrowsAsync<RpcException>(() =>
                client.HandleMessagesAsync(new HandleRequest {
                    Messages = { new ChatMessage { Role = "user", Content = "boom" } }
                }).ResponseAsync);

            Assert.Equal(StatusCode.Internal, ex.StatusCode);
            Assert.Equal("", ex.Status.Detail);
        }
        finally {
            await server.StopServerAsync();
        }
    }

    [Fact]
    public async Task GetCapabilities_Returns_Config_Values() {
        var server = new GrpcServer(0);
        await server.StartServerAsync(_ => Task.FromResult<object>("ok"), TestConfig());
        using var channel = GrpcChannel.ForAddress($"http://localhost:{server.GetPort}");
        var client = new AgentHandlerClient(channel);
        try {
            var caps = await client.GetCapabilitiesAsync(new GetCapabilitiesRequest());

            Assert.Equal("test-agent", caps.Name);
            Assert.Equal("Test agent", caps.Description);
            Assert.Equal("1.2.3", caps.Version);
            Assert.False(caps.SupportsStreaming);
        }
        finally {
            await server.StopServerAsync();
        }
    }

    [Fact]
    public async Task GetCapabilities_Defaults_Version_To_0_1_0() {
        var config = TestConfig();
        config.Version = null!; // Deliberately force the null-default path (CS8625).

        var server = new GrpcServer(0);
        await server.StartServerAsync(_ => Task.FromResult<object>("ok"), config);
        using var channel = GrpcChannel.ForAddress($"http://localhost:{server.GetPort}");
        var client = new AgentHandlerClient(channel);
        try {
            var caps = await client.GetCapabilitiesAsync(new GetCapabilitiesRequest());
            Assert.Equal("0.1.0", caps.Version);
        }
        finally {
            await server.StopServerAsync();
        }
    }

    [Fact]
    public async Task HealthCheck_Reports_Healthy() {
        var server = new GrpcServer(0);
        await server.StartServerAsync(_ => Task.FromResult<object>("ok"), TestConfig());
        using var channel = GrpcChannel.ForAddress($"http://localhost:{server.GetPort}");
        var client = new AgentHandlerClient(channel);
        try {
            var health = await client.HealthCheckAsync(new HealthCheckRequest());

            Assert.True(health.Healthy);
            Assert.Equal("test-agent is healthy", health.Message);
        }
        finally {
            await server.StopServerAsync();
        }
    }
}
