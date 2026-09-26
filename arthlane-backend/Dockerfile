# syntax=docker/dockerfile:1
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
COPY src src
RUN --mount=type=cache,target=/root/.m2 mvn -B -q package -DskipTests

FROM eclipse-temurin:21-jre
RUN useradd --system --uid 10001 arthlane
WORKDIR /app
COPY --from=build /src/target/arthlane-backend-*.jar app.jar
USER arthlane
ENV SPRING_PROFILES_ACTIVE=prod
EXPOSE 8766
ENTRYPOINT ["java", "-Xmx512m", "-jar", "/app/app.jar"]
