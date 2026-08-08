import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/app_exception.dart';
import '../../../core/network/api_client.dart';

class BorrowerActivationRepository {
  final ApiClient _apiClient;

  BorrowerActivationRepository({required ApiClient apiClient})
      : _apiClient = apiClient;

  Future<void> activate({
    required String phoneNumber,
    required String activationCode,
    required String pin,
  }) async {
    try {
      await _apiClient.dio.post(
        '/api/v1/borrower/auth/activate',
        data: {
          'phoneNumber': phoneNumber,
          'activationCode': activationCode,
          'pin': pin,
        },
      );
    } on DioException catch (e) {
      throw parseDioException(e);
    }
  }
}

final activationRepositoryProvider =
    Provider<BorrowerActivationRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return BorrowerActivationRepository(apiClient: apiClient);
});
