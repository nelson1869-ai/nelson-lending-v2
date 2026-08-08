import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Runtime application configuration parsed from environment or build flags.
class AppConfig {
  final String apiBaseUrl;
  final String environment;

  const AppConfig({
    required this.apiBaseUrl,
    required this.environment,
  });

  factory AppConfig.fromEnvironment() {
    const defaultUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000',
    );
    const env = String.fromEnvironment(
      'APP_ENV',
      defaultValue: 'development',
    );

    return const AppConfig(
      apiBaseUrl: defaultUrl,
      environment: env,
    );
  }
}

/// Provider for global application configuration.
final appConfigProvider = Provider<AppConfig>((ref) {
  return AppConfig.fromEnvironment();
});
