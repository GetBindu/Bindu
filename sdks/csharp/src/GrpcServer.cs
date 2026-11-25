using Bindu.Grpc;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Microsoft.Extensions.DependencyInjection;
using System.Net;


namespace Bindu.Sdk {

    /// <summary>
    /// ASP.NET Core gRPC server that hosts the agent's <see cref="AgentHandler"/> so the
    /// Bindu core can deliver tasks to the SDK.
    /// </summary>
    internal class GrpcServer {
        private int _port = 0; //default value
        private int _usedPort = 0;
        private WebApplication? _app;

        /// <summary>Gets the actual port the callback server is listening on (0 until started).</summary>
        public int GetPort => _usedPort;

        /// <summary>
        /// Creates a server configuration for the given port.
        /// </summary>
        /// <param name="port">
        /// Port to listen on, or <c>0</c> to let the OS pick a free port. If the requested
        /// port is already in use, a free port is chosen automatically.
        /// </param>
        public GrpcServer(int port) {
            _port = port;
        }


        //private WebApplication BuildApp

        /// <summary>
        /// Starts the gRPC callback server (HTTP/2) with the given handler and agent config.
        /// </summary>
        /// <param name="handler">Delegate that processes incoming conversation history.</param>
        /// <param name="config">Agent configuration used by the handler service.</param>
        public async Task StartServerAsync(Func<IReadOnlyList<ChatMessage>, Task<object>> handler, AgentConfig config) {
            WebApplication BuildApp(int portToBind) {
                var builder = WebApplication.CreateBuilder();
                builder.Services.AddSingleton(handler);
                builder.Services.AddSingleton(config);

                builder.WebHost.ConfigureKestrel(options => {
                    options.Listen(IPAddress.Loopback, portToBind, listenOptions => {
                        listenOptions.Protocols = HttpProtocols.Http2;
                    });
                });

                builder.Services.AddGrpc();
                var app = builder.Build();
                app.MapGrpcService<AgentHandler>();

                return app;
            }

            _app = BuildApp(_port);

            try {
                await _app.StartAsync();
            }
            catch(IOException) {
                if (_port != 0) {
                    Console.WriteLine($"[bindu-sdk] Port {_port} is in use, picking a free port automatically.");

                    await _app.DisposeAsync();

                    _port = 0; 
                    _app = BuildApp(_port);
                    await _app.StartAsync();
                }
                else {
                    throw; 
                }
            }

            var addressFeature = _app.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>();
            var address = addressFeature?.Addresses.FirstOrDefault();
            _usedPort = new Uri(address!).Port;
        }

        /// <summary>Stops and disposes the underlying web application.</summary>
        public async Task StopServerAsync() {
            if (_app is not null) {
                var app = _app;
                await app.StopAsync();
                await app.DisposeAsync();
                _app = null;
            }
        }

    }
}
