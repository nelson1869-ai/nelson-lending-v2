import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/owner_loans_api_client.dart';
import '../domain/owner_loan_models.dart';

final ownerLoansFilterProvider = StateProvider<String?>((ref) => null);

final ownerLoansListProvider =
    FutureProvider.autoDispose<List<OwnerLoanModel>>((ref) async {
  final client = ref.watch(ownerLoansApiClientProvider);
  final filterStatus = ref.watch(ownerLoansFilterProvider);
  return client.fetchLoans(status: filterStatus);
});

final ownerLoanDetailProvider = FutureProvider.autoDispose
    .family<OwnerLoanDetailModel, String>((ref, loanId) async {
  final client = ref.watch(ownerLoansApiClientProvider);
  return client.fetchLoanDetail(loanId);
});

final ownerLoansControllerProvider =
    StateNotifierProvider<OwnerLoansController, AsyncValue<void>>((ref) {
  return OwnerLoansController(ref);
});

class OwnerLoansController extends StateNotifier<AsyncValue<void>> {
  final Ref _ref;

  OwnerLoansController(this._ref) : super(const AsyncValue.data(null));

  OwnerLoansApiClient get _apiClient => _ref.read(ownerLoansApiClientProvider);

  Future<OwnerLoanModel?> createLoanFromRequest(String requestId) async {
    state = const AsyncValue.loading();
    try {
      final loan = await _apiClient.createLoanFromRequest(requestId);
      _ref.invalidate(ownerLoansListProvider);
      state = const AsyncValue.data(null);
      return loan;
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      return null;
    }
  }

  Future<OwnerLoanModel?> disburseLoan(String loanId) async {
    state = const AsyncValue.loading();
    try {
      final loan = await _apiClient.disburseLoan(loanId);
      _ref.invalidate(ownerLoansListProvider);
      _ref.invalidate(ownerLoanDetailProvider(loanId));
      state = const AsyncValue.data(null);
      return loan;
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      return null;
    }
  }

  Future<OwnerLoanModel?> cancelLoan(String loanId) async {
    state = const AsyncValue.loading();
    try {
      final loan = await _apiClient.cancelLoan(loanId);
      _ref.invalidate(ownerLoansListProvider);
      _ref.invalidate(ownerLoanDetailProvider(loanId));
      state = const AsyncValue.data(null);
      return loan;
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      return null;
    }
  }
}
