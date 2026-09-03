# gateway：服务器1 业务接入网关

网关只做接入：鉴权、限流、统一错误、访问日志、健康检查。  
本模块是库，**没有启动类**。由 `app` 模块组装进同一个进程。

业务接口分别在 `auth`、`circulation`、`ingest`、`project`、`task`、`audit` 模块中实现。

启动见 `server1/app/README.md`：

```bash
cd server1
mvn clean install -DskipTests
mvn -pl app spring-boot:run
```
