import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/loan_request_models.dart';

final loanRequestsApiClientProvider = Provider<LoanRequestsApiClient>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return LoanRequestsApiClient(apiClient.dio);
});

class LoanRequestsApiClient {
  final Dio _dio;

  LoanRequestsApiClient(this._dio);

  Future<LoanQuoteModel> calculateQuote({
    required double principal,
    required int termMonths,
    required String paymentFrequency,
    required String firstDueDate,
  }) async {
    final response = await _dio.post(
      '/borrower/loan-requests/quote',
      data: {
        'principal': principal.toStringAsFixed(2),
        'termMonths': termMonths,
        'paymentFrequency': paymentFrequency,
        'firstDueDate': firstDueDate,
      },
    );
    return LoanQuoteModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<LoanRequestModel> submitRequest({
    required double principal,
    required int termMonths,
    required String paymentFrequency,
    required String firstDueDate,
  }) async {
    final response = await _dio.post(
      '/borrower/loan-requests',
      data: {
        'principal': principal.toStringAsFixed(2),
        'termMonths': termMonths,
        'paymentFrequency': paymentFrequency,
        'firstDueDate': firstDueDate,
      },
    );
    return LoanRequestModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<LoanRequestModel>> listRequests() async {
    final response = await _dio.get('/borrower/loan-requests');
    final list = response.data as List<dynamic>;
    return list
        .map((e) => LoanRequestModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<LoanRequestModel> getRequestDetail(String requestId) async {
    final response = await _dio.get('/borrower/loan-requests/$requestId');
    return LoanRequestModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<LoanRequestModel> cancelRequest(String requestId) async {
    final response =
        await _dio.post('/borrower/loan-requests/$requestId/cancel');
    return LoanRequestModel.fromJson(response.data as Map<String, dynamic>);
  }
}
