// import 'package:flutter_riverpod/flutter_riverpod.dart';

// class AppConfig {
//   final String apiBaseUrl;

//   const AppConfig({
//     required this.apiBaseUrl,
//   });

//   factory AppConfig.fromEnvironment() {
//     const String baseUrl = String.fromEnvironment(
//       'API_BASE_URL',
//       defaultValue: 'http://10.0.2.2:8000',
//     );
//     return const AppConfig(apiBaseUrl: baseUrl);
//   }
// }

// final appConfigProvider = Provider<AppConfig>((ref) {
//   return AppConfig.fromEnvironment();
// });

import 'package:flutter_riverpod/flutter_riverpod.dart';

class AppConfig {
  final String apiBaseUrl;

  const AppConfig({
    required this.apiBaseUrl,
  });

  factory AppConfig.fromEnvironment() {
    const String baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'https://lending-nelson-v2-api.onrender.com',
    );

    return const AppConfig(
      apiBaseUrl: baseUrl,
    );
  }
}

final appConfigProvider = Provider<AppConfig>((ref) {
  return AppConfig.fromEnvironment();
});