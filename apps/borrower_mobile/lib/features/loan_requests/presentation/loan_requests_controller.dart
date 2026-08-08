import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/loan_requests_api_client.dart';
import '../domain/loan_request_models.dart';

class LoanRequestsState {
  final bool isLoading;
  final String? errorMessage;
  final List<LoanRequestModel> requests;
  final LoanQuoteModel? currentQuote;
  final bool isQuoteLoading;

  const LoanRequestsState({
    this.isLoading = false,
    this.errorMessage,
    this.requests = const [],
    this.currentQuote,
    this.isQuoteLoading = false,
  });

  LoanRequestsState copyWith({
    bool? isLoading,
    String? errorMessage,
    List<LoanRequestModel>? requests,
    LoanQuoteModel? currentQuote,
    bool clearQuote = false,
    bool? isQuoteLoading,
  }) {
    return LoanRequestsState(
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
      requests: requests ?? this.requests,
      currentQuote: clearQuote ? null : (currentQuote ?? this.currentQuote),
      isQuoteLoading: isQuoteLoading ?? this.isQuoteLoading,
    );
  }
}

final loanRequestsControllerProvider =
    StateNotifierProvider<LoanRequestsController, LoanRequestsState>((ref) {
  final client = ref.watch(loanRequestsApiClientProvider);
  return LoanRequestsController(client);
});

class LoanRequestsController extends StateNotifier<LoanRequestsState> {
  final LoanRequestsApiClient _client;

  LoanRequestsController(this._client) : super(const LoanRequestsState());

  Future<void> fetchRequests() async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      final list = await _client.listRequests();
      state = state.copyWith(isLoading: false, requests: list);
    } on DioException catch (e) {
      final msg = e.response?.data is Map
          ? (e.response?.data['detail']?.toString() ?? e.message)
          : e.message;
      state = state.copyWith(isLoading: false, errorMessage: msg);
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
    }
  }

  Future<LoanQuoteModel?> calculateQuote({
    required double principal,
    required double monthlyRate,
    required int termMonths,
    required String paymentFrequency,
    required String firstDueDate,
  }) async {
    state = state.copyWith(isQuoteLoading: true, errorMessage: null);
    try {
      final quote = await _client.calculateQuote(
        principal: principal,
        monthlyRate: monthlyRate,
        termMonths: termMonths,
        paymentFrequency: paymentFrequency,
        firstDueDate: firstDueDate,
      );
      state = state.copyWith(isQuoteLoading: false, currentQuote: quote);
      return quote;
    } on DioException catch (e) {
      final msg = e.response?.data is Map
          ? (e.response?.data['detail']?.toString() ?? e.message)
          : e.message;
      state = state.copyWith(
          isQuoteLoading: false, clearQuote: true, errorMessage: msg);
      return null;
    } catch (e) {
      state = state.copyWith(
          isQuoteLoading: false, clearQuote: true, errorMessage: e.toString());
      return null;
    }
  }

  Future<bool> submitRequest({
    required double principal,
    required double monthlyRate,
    required int termMonths,
    required String paymentFrequency,
    required String firstDueDate,
  }) async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      await _client.submitRequest(
        principal: principal,
        monthlyRate: monthlyRate,
        termMonths: termMonths,
        paymentFrequency: paymentFrequency,
        firstDueDate: firstDueDate,
      );
      state = state.copyWith(isLoading: false, clearQuote: true);
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

  Future<bool> cancelRequest(String requestId) async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      await _client.cancelRequest(requestId);
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
