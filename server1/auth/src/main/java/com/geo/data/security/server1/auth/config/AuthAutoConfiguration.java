package com.geo.data.security.server1.auth.config;

import com.geo.data.security.server1.auth.store.InMemoryTokenSessionStore;
import com.geo.data.security.server1.auth.store.TokenSessionStore;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(AuthProperties.class)
public class AuthAutoConfiguration {

    /**
     * 本地默认：JVM 内存会话表。不依赖 Redis，重启后会话清空需重新登录。
     */
    @Bean
    @ConditionalOnMissingBean(TokenSessionStore.class)
    public TokenSessionStore inMemoryTokenSessionStore() {
        return new InMemoryTokenSessionStore();
    }
}
