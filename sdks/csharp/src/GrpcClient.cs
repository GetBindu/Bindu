using Bindu.Grpc;
using Grpc.Core;
using Grpc.Net.Client;
using System.Text.Json;
using static Bindu.Grpc.BinduService;

namespace Bindu.Sdk {
    /// <summary>
    /// gRPC client used to talk to the Bindu core on port 3774 (register agents,
    /// unregister agents, and send heartbeats).
    /// </summary>
    internal class GrpcClient : IDisposable {
        private BinduServiceClient? _binduClient;
        private GrpcChannel? _channel;
        private GrpcServer? _grpcServer;
        private readonly string _coreAddress;

        /// <summary>
        /// Creates a gRPC client for the Bindu core.
        /// </summary>
        /// <param name="coreAddress">
        /// Base address of the core's gRPC server. Defaults to <c>http://localhost:3774</c>.
        /// </param>
        public GrpcClient(string coreAddress = "http://localhost:3774/") {
            _coreAddress = coreAddress;
        }

        /// <summary>
        /// Creates a channel and client connected to the Bindu core at
        /// <c>http://localhost:3774</c>.
        /// </summary>
        /// <param name="grpcServer">The SDK's callback server; its actual port is reported
        /// to the core during registration.</param>
        /// <returns>The initialized core client.</returns>
        public BinduServiceClient InitializeBinduClient(GrpcServer grpcServer) {
            _channel = GrpcChannel.ForAddress(_coreAddress);

            var client = new BinduServiceClient(_channel);
            _binduClient = client;
            _grpcServer = grpcServer;
            return _binduClient;
        }

        /// <summary>
        /// Registers the agent described by <paramref name="regDetails"/> with the Bindu core.
        /// </summary>
        /// <param name="regDetails">Agent configuration to register.</param>
        /// <returns>The core's registration response, or <c>null</c> if the client is not initialized.</returns>
        /// <exception cref="InvalidOperationException">
        /// Thrown when the core rejects the registration (its response has
        /// <c>Success == false</c>).
        /// </exception>
        public async Task<RegisterAgentResponse?> RegisterAgent(AgentConfig regDetails) {
            if (_binduClient == null) { return null; }
            var configJson = new {
                author = regDetails.Author,
                name = regDetails.Name,
                description = regDetails.Description,
                deployment = new {
                    url = regDetails.DeploymentUrl,
                    expose = regDetails.ExposeDeployment,
                },
                kind = "agent"
            };


            var json = JsonSerializer.Serialize(configJson);

            var regRequest = new RegisterAgentRequest {
                ConfigJson = json,
                GrpcCallbackAddress = $"localhost:{_grpcServer!.GetPort}"
            };

            var options = new CallOptions(deadline: DateTime.UtcNow.AddSeconds(10));

            var response = await _binduClient.RegisterAgentAsync(regRequest, options);
            if (!response.Success) {
                throw new InvalidOperationException($"Bindu agent registration failed: {response.Error}");
            }

            return response;
        }

        /// <summary>
        /// Unregisters the agent from the core and releases the client.
        /// </summary>
        /// <param name="regDetails">The registration result of the agent to unregister.</param>
        /// <returns>The core's unregister response, or <c>null</c> if the client is not initialized.</returns>
        public UnregisterAgentResponse? UnRegisterAgent(RegistrationResult regDetails) {
            var unRegister = new UnregisterAgentRequest {
                AgentId = regDetails.AgentId
            };
            try {
                var options = new CallOptions(deadline: DateTime.UtcNow.AddSeconds(10));
                return _binduClient?.UnregisterAgent(unRegister, options);
            }
            catch (RpcException) {
                return null;
            }
            finally {
                _channel?.Dispose();
                _channel = null;
                _binduClient = null;
            }
        }

        public void Dispose() {
            _channel?.Dispose();
            _channel = null;
        }

    }

}
