import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/borrower_loan_models.dart';
import '../domain/borrower_payment_models.dart';

final borrowerLoansApiClientProvider = Provider<BorrowerLoansApiClient>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return BorrowerLoansApiClient(apiClient.dio);
});

class BorrowerLoansApiClient {
  final Dio _dio;

  BorrowerLoansApiClient(this._dio);

  Future<List<BorrowerLoanModel>> fetchLoans() async {
    final res = await _dio.get('/api/v1/borrower/loans');
    final list = res.data as List<dynamic>;
    return list
        .map((e) => BorrowerLoanModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<BorrowerLoanDetailModel> fetchLoanDetail(String id) async {
    final res = await _dio.get('/api/v1/borrower/loans/$id');
    return BorrowerLoanDetailModel.fromJson(res.data as Map<String, dynamic>);
  }

  Future<List<BorrowerPaymentModel>> fetchLoanPayments(String loanId) async {
    final res = await _dio.get('/api/v1/borrower/loans/$loanId/payments');
    final list = res.data as List<dynamic>;
    return list
        .map((e) => BorrowerPaymentModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}
