using Bindu.Sdk;

namespace Bindu.Sdk.Tests;

public class AgentConfigTests {
    [Fact]
    public void Defaults_Are_As_Documented() {
        var config = new AgentConfig {
            Author = "dev@example.com",
            Name = "test-agent",
            Description = "A test agent"
        };

        Assert.Equal(0, config.GrpcCallbackPort);
        Assert.Equal("http://localhost:3773", config.DeploymentUrl);
        Assert.Equal(3774, config.CoreGrpcPort);
        Assert.False(config.ExposeDeployment);
        Assert.Empty(config.Skills);
        Assert.Equal("0.1.0", config.Version);
    }

    [Fact]
    public void Properties_Are_Settable() {
        var config = new AgentConfig {
            Author = "author@example.com",
            Name = "custom-agent",
            Description = "Custom description",
            GrpcCallbackPort = 5052,
            DeploymentUrl = "http://localhost:9000",
            CoreGrpcPort = 5774,
            ExposeDeployment = true,
            Skills = ["skill-a", "skill-b"],
            Version = "2.1.0"
        };

        Assert.Equal("author@example.com", config.Author);
        Assert.Equal("custom-agent", config.Name);
        Assert.Equal("Custom description", config.Description);
        Assert.Equal(5052, config.GrpcCallbackPort);
        Assert.Equal("http://localhost:9000", config.DeploymentUrl);
        Assert.Equal(5774, config.CoreGrpcPort);
        Assert.True(config.ExposeDeployment);
        Assert.Equal(["skill-a", "skill-b"], config.Skills);
        Assert.Equal("2.1.0", config.Version);
    }
}
