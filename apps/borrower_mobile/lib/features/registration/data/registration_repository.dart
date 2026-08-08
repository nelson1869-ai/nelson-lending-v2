import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/app_exception.dart';
import '../../../core/network/api_client.dart';

class BorrowerRegistrationData {
  final String firstName;
  final String lastName;
  final String nationalId;
  final String phoneNumber;
  final String address;
  final DateTime dateOfBirth;

  const BorrowerRegistrationData({
    required this.firstName,
    required this.lastName,
    required this.nationalId,
    required this.phoneNumber,
    required this.address,
    required this.dateOfBirth,
  });

  Map<String, dynamic> toJson() => {
        'firstName': firstName,
        'lastName': lastName,
        'nationalId': nationalId,
        'phoneNumber': phoneNumber,
        'address': address,
        'dateOfBirth':
            "${dateOfBirth.year.toString().padLeft(4, '0')}-${dateOfBirth.month.toString().padLeft(2, '0')}-${dateOfBirth.day.toString().padLeft(2, '0')}",
      };
}

class BorrowerRegistrationResponseData {
  final String registrationId;
  final String status;
  final DateTime submittedAt;
  final String message;

  const BorrowerRegistrationResponseData({
    required this.registrationId,
    required this.status,
    required this.submittedAt,
    required this.message,
  });

  factory BorrowerRegistrationResponseData.fromJson(Map<String, dynamic> json) {
    return BorrowerRegistrationResponseData(
      registrationId: json['registrationId'] as String? ??
          json['registration_id'] as String,
      status: json['status'] as String,
      submittedAt: DateTime.parse(
          json['submittedAt'] as String? ?? json['submitted_at'] as String),
      message: json['message'] as String,
    );
  }
}

class BorrowerRegistrationRepository {
  final ApiClient _apiClient;

  BorrowerRegistrationRepository({required ApiClient apiClient})
      : _apiClient = apiClient;

  Future<BorrowerRegistrationResponseData> register(
      BorrowerRegistrationData data) async {
    try {
      final response = await _apiClient.dio.post(
        '/api/v1/borrower/registrations',
        data: data.toJson(),
      );
      return BorrowerRegistrationResponseData.fromJson(
          response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw parseDioException(e);
    }
  }
}

final registrationRepositoryProvider =
    Provider<BorrowerRegistrationRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return BorrowerRegistrationRepository(apiClient: apiClient);
});
