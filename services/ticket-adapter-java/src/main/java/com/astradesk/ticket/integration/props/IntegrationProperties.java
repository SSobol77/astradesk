package com.astradesk.ticket.integration.props;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.NestedConfigurationProperty;
import org.springframework.validation.annotation.Validated;

import jakarta.validation.constraints.NotBlank;

/**
 * Configuration properties describing how the adapter talks to external systems.
 *
 * <p>The structure mirrors {@code application.yml}. Validation ensures missing critical
 * settings are caught at startup instead of failing during runtime calls.</p>
 */
@Validated
@ConfigurationProperties(prefix = "integration")
public class IntegrationProperties {

    @NestedConfigurationProperty
    private final JiraProperties jira = new JiraProperties();

    @NestedConfigurationProperty
    private final SlackProperties slack = new SlackProperties();

    @NestedConfigurationProperty
    private final FrontendProperties frontend = new FrontendProperties();

    public JiraProperties getJira() {
        return jira;
    }

    public SlackProperties getSlack() {
        return slack;
    }

    public FrontendProperties getFrontend() {
        return frontend;
    }

    public static class JiraProperties {

        /**
         * Quick kill switch – keep the app running even when Jira is temporarily disabled.
         */
        private boolean enabled = true;

        @NotBlank
        private String baseUrl = "https://example.atlassian.net";

        @NotBlank
        private String username = "jira-bot@example.com";

        @NotBlank
        private String apiToken = "changeme";

        @NotBlank
        private String projectKey = "ASTRA";

        @NotBlank
        private String issueType = "Task";

        @NotBlank
        private String defaultPriority = "Medium";

        public boolean isEnabled() {
            return enabled;
        }

        public void setEnabled(boolean enabled) {
            this.enabled = enabled;
        }

        public String getBaseUrl() {
            return baseUrl;
        }

        public void setBaseUrl(String baseUrl) {
            this.baseUrl = baseUrl;
        }

        public String getUsername() {
            return username;
        }

        public void setUsername(String username) {
            this.username = username;
        }

        public String getApiToken() {
            return apiToken;
        }

        public void setApiToken(String apiToken) {
            this.apiToken = apiToken;
        }

        public String getProjectKey() {
            return projectKey;
        }

        public void setProjectKey(String projectKey) {
            this.projectKey = projectKey;
        }

        public String getIssueType() {
            return issueType;
        }

        public void setIssueType(String issueType) {
            this.issueType = issueType;
        }

        public String getDefaultPriority() {
            return defaultPriority;
        }

        public void setDefaultPriority(String defaultPriority) {
            this.defaultPriority = defaultPriority;
        }
    }

    public static class SlackProperties {

        private boolean enabled = false;

        private String webhookUrl = "https://hooks.slack.com/services/XXXXX/XXXXX/XXXXXXXX";

        private String defaultChannel = null;

        public boolean isEnabled() {
            return enabled;
        }

        public void setEnabled(boolean enabled) {
            this.enabled = enabled;
        }

        public String getWebhookUrl() {
            return webhookUrl;
        }

        public void setWebhookUrl(String webhookUrl) {
            this.webhookUrl = webhookUrl;
        }

        public String getDefaultChannel() {
            return defaultChannel;
        }

        public void setDefaultChannel(String defaultChannel) {
            this.defaultChannel = defaultChannel;
        }
    }

    public static class FrontendProperties {

        @NotBlank
        private String baseUrl = "https://app.astradesk.local";

        public String getBaseUrl() {
            return baseUrl;
        }

        public void setBaseUrl(String baseUrl) {
            this.baseUrl = baseUrl;
        }
    }
}
