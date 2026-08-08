import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/owner_loan_models.dart';
import '../domain/owner_payment_models.dart';

final ownerLoansApiClientProvider = Provider<OwnerLoansApiClient>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return OwnerLoansApiClient(apiClient.dio);
});

class OwnerLoansApiClient {
  final Dio _dio;

  OwnerLoansApiClient(this._dio);

  Future<List<OwnerLoanModel>> fetchLoans({String? status}) async {
    final queryParams = <String, dynamic>{};
    if (status != null && status.isNotEmpty) {
      queryParams['status'] = status;
    }
    final res = await _dio.get('/owner/loans', queryParameters: queryParams);
    final list = res.data as List<dynamic>;
    return list
        .map((e) => OwnerLoanModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<OwnerLoanDetailModel> fetchLoanDetail(String id) async {
    final res = await _dio.get('/owner/loans/$id');
    return OwnerLoanDetailModel.fromJson(res.data as Map<String, dynamic>);
  }

  Future<OwnerLoanModel> createLoanFromRequest(String requestId) async {
    final res = await _dio.post('/owner/loan-requests/$requestId/create-loan');
    return OwnerLoanModel.fromJson(res.data as Map<String, dynamic>);
  }

  Future<OwnerLoanModel> disburseLoan(String loanId) async {
    final res = await _dio.post('/owner/loans/$loanId/disburse');
    return OwnerLoanModel.fromJson(res.data as Map<String, dynamic>);
  }

  Future<OwnerLoanModel> cancelLoan(String loanId) async {
    final res = await _dio.post('/owner/loans/$loanId/cancel');
    return OwnerLoanModel.fromJson(res.data as Map<String, dynamic>);
  }

  Future<OwnerPaymentModel> postPayment(
    String loanId, {
    required String amount,
    required String paymentDate,
    String? reference,
    String? note,
    String? idempotencyKey,
  }) async {
    final key = idempotencyKey ??
        'idem-${DateTime.now().microsecondsSinceEpoch}-${loanId.replaceAll('-', '').substring(0, 8)}';
    final body = <String, dynamic>{
      'amount': amount,
      'paymentDate': paymentDate,
      if (reference != null && reference.isNotEmpty) 'reference': reference,
      if (note != null && note.isNotEmpty) 'note': note,
      'idempotencyKey': key,
    };
    final res = await _dio.post(
      '/owner/loans/$loanId/payments',
      data: body,
      options: Options(headers: {'Idempotency-Key': key}),
    );
    return OwnerPaymentModel.fromJson(res.data as Map<String, dynamic>);
  }

  Future<List<OwnerPaymentModel>> fetchLoanPayments(String loanId) async {
    final res = await _dio.get('/owner/loans/$loanId/payments');
    final list = res.data as List<dynamic>;
    return list
        .map((e) => OwnerPaymentModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}
