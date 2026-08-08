import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/borrower_loans_api_client.dart';
import '../domain/borrower_loan_models.dart';

final borrowerLoansListProvider =
    FutureProvider.autoDispose<List<BorrowerLoanModel>>((ref) async {
  final client = ref.watch(borrowerLoansApiClientProvider);
  return client.fetchLoans();
});

final borrowerLoanDetailProvider = FutureProvider.autoDispose
    .family<BorrowerLoanDetailModel, String>((ref, loanId) async {
  final client = ref.watch(borrowerLoansApiClientProvider);
  return client.fetchLoanDetail(loanId);
});
