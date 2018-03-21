import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4
import requests
from flask import Flask, jsonify, request


class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        # Create Genesis Block
        self.new_block(proof=100, previous_hash=1)

    def new_block(self, proof, previous_hash=None):
        """
        Create a new Block in the Blockchain
        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """

        block = {
            'index' : len(self.chain) + 1,
            'transactions' : self.current_transactions,
            'timestamp' : time(),
            'previous_hash' : previous_hash or self.hash(self.last_block),
            'proof' : proof
        }

        # Reset the current transactions
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block
        :param sender: <str> Address of the Sender
        :param recipient: <str> Address of the Recipient
        :param amount: <int> Amount
        :return: <int> The index of the Block that will hold this transaction
        """

        self.current_transactions.append({
            'sender' : sender,
            'recipient' : recipient,
            'amount' : amount
        })

        return len(self.chain) + 1

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block
        :param block: <dict> Block
        :return: <str>
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_str = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_str).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
         - p is the previous proof, and p' is the new proof

        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not.
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: <str> Address of node. Eg. 'http://192.168.0.5:5000'
        :return: None
        """

        url = urlparse(address)
        self.nodes.add(url.netloc)

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        :param chain: <list> A blockchain
        :return: <bool> True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]

            print(f'{last_block}')
            print(f'{block}')
            print('\n----------\n')

            # Validate hash of the block
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Check the proof of work is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            # Move to next block for validation
            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        This is our Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: <bool> True if our chain was replaced, False if not
        """

        neighbors = self.nodes
        new_chain = None

        # Look for chains longer than ours
        max_length = len(self.chain)

        for node in neighbors:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # If neighbors chain is longer and is valid, keep that chain as longest
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return False


# Instantiate App
app = Flask(__name__)

# Generate a globally unique identifier for the node
node_identifier = str(uuid4()).replace('-','')

# Instantiate Blockchain
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    # Run the proof of work algorithm to get the next proof
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # Add a new transaction for the mined block with 0 as the sender to mark this block mined
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1
    )

    # Add the new block to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': 'New Block Forged',
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }

    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    transaction_obj = request.get_json()

    required_params = ['sender', 'recipient', 'amount']

    if not all(param in transaction_obj for param in required_params):
        return f'Missing a required parameter: {param}', 400

    block_index = blockchain.new_transaction(transaction_obj['sender'], transaction_obj['recipient'], transaction_obj['amount'])

    response = {
        'message' : f'Transaction will be added to Block {block_index}'
    }
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain' : blockchain.chain,
        'length' : len(blockchain.chain)
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added to the Blockchain',
        'total_nodes': list(blockchain.nodes)
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our blockchain was replaced',
            'new_chain': blockchain.chain
        }

    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 201


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
