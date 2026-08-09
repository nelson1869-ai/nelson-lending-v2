import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/owner_borrower_model.dart';

final ownerBorrowersApiClientProvider = Provider((ref) => OwnerBorrowersApiClient(ref.watch(apiClientProvider).dio));

class OwnerBorrowersApiClient {
  final Dio _dio;
  OwnerBorrowersApiClient(this._dio);

  Future<List<OwnerBorrowerModel>> listBorrowers({String? search}) async {
    final response = await _dio.get('/api/v1/owner/borrowers', queryParameters: {
      if (search != null && search.trim().isNotEmpty) 'search': search.trim(),
    });
    return (response.data as List<dynamic>)
        .map((item) => OwnerBorrowerModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}
