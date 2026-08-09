import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/dashboard_models.dart';

final ownerReportsApiClientProvider = Provider<OwnerReportsApiClient>((ref) {
  return OwnerReportsApiClient(ref.watch(apiClientProvider).dio);
});

class OwnerReportsApiClient {
  final Dio _dio;

  OwnerReportsApiClient(this._dio);

  Future<OwnerDashboardModel> fetchDashboard({
    required DateTime fromDate,
    required DateTime toDate,
  }) async {
    final response = await _dio.get(
      '/api/v1/owner/reports/dashboard',
      queryParameters: {
        'from_date': _dateOnly(fromDate),
        'to_date': _dateOnly(toDate),
      },
    );
    return OwnerDashboardModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<int> accrueDueInterest() async {
    final response = await _dio.post('/api/v1/owner/loans/accrue-interest');
    return (response.data['loans_updated'] as num).toInt();
  }

  static String _dateOnly(DateTime value) {
    final month = value.month.toString().padLeft(2, '0');
    final day = value.day.toString().padLeft(2, '0');
    return '${value.year}-$month-$day';
  }
}
