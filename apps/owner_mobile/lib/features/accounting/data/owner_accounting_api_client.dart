import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/accounting_models.dart';

final ownerAccountingApiClientProvider =
    Provider<OwnerAccountingApiClient>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return OwnerAccountingApiClient(apiClient.dio);
});

class OwnerAccountingApiClient {
  final Dio _dio;

  OwnerAccountingApiClient(this._dio);

  Future<List<AccountModel>> fetchAccounts() async {
    final res = await _dio.get('/owner/accounting/accounts');
    final list = res.data as List<dynamic>;
    return list
        .map((e) => AccountModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<JournalTransactionModel>> fetchJournals() async {
    final res = await _dio.get('/owner/accounting/journals');
    final list = res.data as List<dynamic>;
    return list
        .map((e) => JournalTransactionModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<JournalTransactionModel> fetchJournalDetail(String id) async {
    final res = await _dio.get('/owner/accounting/journals/$id');
    return JournalTransactionModel.fromJson(res.data as Map<String, dynamic>);
  }

  Future<JournalTransactionModel> reverseJournal(
    String id, {
    String? reason,
  }) async {
    final body = <String, dynamic>{
      if (reason != null && reason.isNotEmpty) 'reason': reason,
    };
    final res = await _dio.post(
      '/owner/accounting/journals/$id/reverse',
      data: body,
    );
    return JournalTransactionModel.fromJson(res.data as Map<String, dynamic>);
  }
}
