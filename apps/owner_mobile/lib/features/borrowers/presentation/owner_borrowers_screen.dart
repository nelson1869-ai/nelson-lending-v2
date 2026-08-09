import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/owner_borrowers_api_client.dart';
import '../domain/owner_borrower_model.dart';

class OwnerBorrowersScreen extends ConsumerStatefulWidget {
  const OwnerBorrowersScreen({super.key});
  @override
  ConsumerState<OwnerBorrowersScreen> createState() => _OwnerBorrowersScreenState();
}

class _OwnerBorrowersScreenState extends ConsumerState<OwnerBorrowersScreen> {
  final _search = TextEditingController();
  late Future<List<OwnerBorrowerModel>> _borrowers;

  @override
  void initState() { super.initState(); _borrowers = _load(); }
  Future<List<OwnerBorrowerModel>> _load() => ref.read(ownerBorrowersApiClientProvider).listBorrowers(search: _search.text);

  @override
  void dispose() { _search.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Borrowers')),
        body: Column(children: [
          Padding(padding: const EdgeInsets.all(16), child: TextField(
            controller: _search,
            decoration: const InputDecoration(labelText: 'Search borrowers', prefixIcon: Icon(Icons.search), border: OutlineInputBorder()),
            onSubmitted: (_) => setState(() => _borrowers = _load()),
          )),
          Expanded(child: FutureBuilder<List<OwnerBorrowerModel>>(
            future: _borrowers,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text('Unable to load borrowers',
                            style: TextStyle(color: Colors.red)),
                        const SizedBox(height: 8),
                        Text('${snapshot.error}', textAlign: TextAlign.center),
                        const SizedBox(height: 16),
                        ElevatedButton(
                          onPressed: () => setState(() => _borrowers = _load()),
                          child: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                );
              }
              if (!snapshot.hasData) {
                return const Center(child: Text('No borrowers found.'));
              }
              if (snapshot.data!.isEmpty) return const Center(child: Text('No borrowers found.'));
              return RefreshIndicator(onRefresh: () async => setState(() => _borrowers = _load()), child: ListView.builder(
                itemCount: snapshot.data!.length,
                itemBuilder: (_, index) { final borrower = snapshot.data![index]; return ListTile(
                  leading: const CircleAvatar(child: Icon(Icons.person)),
                  title: Text(borrower.fullName),
                  subtitle: Text('${borrower.phoneNumber}\nNational ID: ${borrower.nationalId}'),
                  isThreeLine: true,
                  trailing: Chip(label: Text(borrower.status)),
                ); },
              ));
            },
          )),
        ]),
      );
}
