import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/owner_loan_requests_api_client.dart';
import '../domain/owner_loan_request_models.dart';

class OwnerLoanRequestsState {
  final bool isLoading;
  final String? errorMessage;
  final List<OwnerLoanRequestDetailModel> requests;
  final String selectedFilter;

  const OwnerLoanRequestsState({
    this.isLoading = false,
    this.errorMessage,
    this.requests = const [],
    this.selectedFilter = 'pending',
  });

  OwnerLoanRequestsState copyWith({
    bool? isLoading,
    String? errorMessage,
    List<OwnerLoanRequestDetailModel>? requests,
    String? selectedFilter,
  }) {
    return OwnerLoanRequestsState(
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
      requests: requests ?? this.requests,
      selectedFilter: selectedFilter ?? this.selectedFilter,
    );
  }
}

final ownerLoanRequestsControllerProvider =
    StateNotifierProvider<OwnerLoanRequestsController, OwnerLoanRequestsState>(
        (ref) {
  final client = ref.watch(ownerLoanRequestsApiClientProvider);
  return OwnerLoanRequestsController(client);
});

class OwnerLoanRequestsController
    extends StateNotifier<OwnerLoanRequestsState> {
  final OwnerLoanRequestsApiClient _client;

  OwnerLoanRequestsController(this._client)
      : super(const OwnerLoanRequestsState());

  Future<void> fetchRequests([String? filter]) async {
    final statusFilter = filter ?? state.selectedFilter;
    state = state.copyWith(
      isLoading: true,
      errorMessage: null,
      selectedFilter: statusFilter,
    );
    try {
      final filterQuery = statusFilter == 'all' ? null : statusFilter;
      final list = await _client.listRequests(statusFilter: filterQuery);
      state = state.copyWith(isLoading: false, requests: list);
    } on DioException catch (e) {
      final msg = e.response?.data is Map
          ? (e.response?.data['detail']?.toString() ?? e.message)
          : e.message;
      state = state.copyWith(isLoading: false, errorMessage: msg);
    } catch (_) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: 'Unable to load loan requests. Please try again.',
      );
    }
  }

  Future<bool> approveRequest(String requestId, {String? ownerNote}) async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      await _client.approveRequest(requestId, ownerNote: ownerNote);
      state = state.copyWith(isLoading: false);
      await fetchRequests();
      return true;
    } on DioException catch (e) {
      final msg = e.response?.data is Map
          ? (e.response?.data['detail']?.toString() ?? e.message)
          : e.message;
      state = state.copyWith(isLoading: false, errorMessage: msg);
      return false;
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
      return false;
    }
  }

  Future<bool> rejectRequest(String requestId, {String? ownerNote}) async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      await _client.rejectRequest(requestId, ownerNote: ownerNote);
      state = state.copyWith(isLoading: false);
      await fetchRequests();
      return true;
    } on DioException catch (e) {
      final msg = e.response?.data is Map
          ? (e.response?.data['detail']?.toString() ?? e.message)
          : e.message;
      state = state.copyWith(isLoading: false, errorMessage: msg);
      return false;
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
      return false;
    }
  }
}
